from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

from app.core.database import get_neo4j_connection
from app.schemas.models import (
    GenreFlowData,
    GenreFlowLink,
    GenreFlowNode,
    GenreFlowSeries,
    GenreFlowSeriesPoint,
)
from app.services.local_graph import load_local_graph


LOCAL_GRAPH = load_local_graph()


class GenreFlowService:
    def __init__(self) -> None:
        self.db = get_neo4j_connection()

    def _generate_evidence_id(self, params: dict[str, Any]) -> str:
        return hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:12]

    def get_sankey_data(
        self,
        start_year: int,
        end_year: int,
        source_genre: str | None = None,
        limit: int = 100,
    ) -> GenreFlowData:
        params = {
            "start_year": start_year,
            "end_year": end_year,
            "source_genre": source_genre,
            "limit": limit,
        }
        _ = self._generate_evidence_id(params)

        with self.db.session() as session:
            if session is None:
                flows: dict[tuple[str, str], int] = defaultdict(int)
                genres: set[str] = set()
                for edge in LOCAL_GRAPH.links:
                    if edge.get("Edge Type") != "InStyleOf":
                        continue
                    source = LOCAL_GRAPH.node_by_id.get(str(edge.get("source")))
                    target = LOCAL_GRAPH.node_by_id.get(str(edge.get("target")))
                    if source is None or target is None:
                        continue
                    if source.get("Node Type") not in {"Song", "Album"}:
                        continue
                    if target.get("Node Type") not in {"Song", "Album"}:
                        continue
                    try:
                        s_year = int(str(source.get("release_date"))[:4])
                        t_year = int(str(target.get("release_date"))[:4])
                    except (TypeError, ValueError):
                        continue
                    if s_year < start_year or s_year > end_year or t_year < start_year or t_year > end_year:
                        continue
                    s_genre = source.get("genre")
                    t_genre = target.get("genre")
                    if not s_genre or not t_genre or s_genre == t_genre:
                        continue
                    if source_genre and source_genre not in {str(s_genre), str(t_genre)}:
                        continue
                    flows[(str(s_genre), str(t_genre))] += 1
                    genres.add(str(s_genre))
                    genres.add(str(t_genre))

                items = sorted(flows.items(), key=lambda item: item[1], reverse=True)[:limit]
                nodes = [GenreFlowNode(id=g, name=g) for g in sorted(genres)]
                links = [GenreFlowLink(source=s, target=t, value=v) for (s, t), v in items]
                return GenreFlowData(nodes=nodes, links=links, series=None)

            genre_filter_clause = "AND song.genre = $source_genre" if source_genre else ""
            query = f"""
            MATCH (song:Song)-[:IN_STYLE_OF]->(style_source)
            WHERE toInteger(song.release_date) >= $start_year
              AND toInteger(song.release_date) <= $end_year
              AND song.genre IS NOT NULL
              AND (
                (style_source:Song AND style_source.genre IS NOT NULL)
                OR (style_source:Album AND style_source.genre IS NOT NULL)
                OR (style_source:Person AND style_source.inferred_genre IS NOT NULL)
                OR (style_source:MusicalGroup AND style_source.inferred_genre IS NOT NULL)
              )
              AND song.genre <> coalesce(style_source.genre, style_source.inferred_genre)
              {genre_filter_clause}
            WITH song.genre as source_genre,
                 coalesce(style_source.genre, style_source.inferred_genre) as target_genre,
                 count(*) as flow_count
            RETURN source_genre, target_genre, flow_count
            ORDER BY flow_count DESC
            LIMIT $limit
            """
            result = session.run(
                query,
                start_year=start_year,
                end_year=end_year,
                source_genre=source_genre,
                limit=limit,
            )
            nodes_set = set()
            links_list = []
            for record in result:
                source = record["source_genre"]
                target = record["target_genre"]
                value = int(record["flow_count"])
                nodes_set.add(source)
                nodes_set.add(target)
                links_list.append(GenreFlowLink(source=source, target=target, value=value))
            nodes = [GenreFlowNode(id=name, name=name) for name in sorted(nodes_set)]
            return GenreFlowData(nodes=nodes, links=links_list, series=None)

    def get_streamgraph_data(
        self,
        start_year: int,
        end_year: int,
        limit: int = 50,
    ) -> GenreFlowData:
        params = {"start_year": start_year, "end_year": end_year, "limit": limit}
        _ = self._generate_evidence_id(params)

        with self.db.session() as session:
            if session is None:
                genre_data: dict[str, list[GenreFlowSeriesPoint]] = defaultdict(list)
                counts: dict[tuple[str, int], int] = defaultdict(int)
                for node in LOCAL_GRAPH.nodes:
                    if node.get("Node Type") not in {"Song", "Album"}:
                        continue
                    try:
                        year = int(str(node.get("release_date"))[:4])
                    except (TypeError, ValueError):
                        continue
                    if year < start_year or year > end_year:
                        continue
                    genre = node.get("genre")
                    if not genre:
                        continue
                    counts[(str(genre), year)] += 1
                for (genre, year), value in counts.items():
                    genre_data[genre].append(GenreFlowSeriesPoint(year=year, value=float(value)))
                series = [
                    GenreFlowSeries(genre=genre, points=sorted(points, key=lambda x: x.year))
                    for genre, points in sorted(genre_data.items())
                ]
                return GenreFlowData(nodes=None, links=None, series=series[:limit])

            query = """
            MATCH (s:Song)
            WHERE toInteger(s.release_date) >= $start_year
              AND toInteger(s.release_date) <= $end_year
              AND s.genre IS NOT NULL
            RETURN s.genre as genre, s.release_date as year, count(*) as song_count
            ORDER BY genre, year
            """
            result = session.run(query, start_year=start_year, end_year=end_year)
            genre_data: dict[str, list[GenreFlowSeriesPoint]] = defaultdict(list)
            for record in result:
                genre = record["genre"]
                year = record["year"]
                try:
                    y = int(year)
                except (TypeError, ValueError):
                    continue
                genre_data[str(genre)].append(GenreFlowSeriesPoint(year=y, value=float(record["song_count"])))
            series = [
                GenreFlowSeries(genre=genre, points=sorted(points, key=lambda x: x.year))
                for genre, points in sorted(genre_data.items())
            ]
            return GenreFlowData(nodes=None, links=None, series=series[:limit])

    def get_genre_stats(self, start_year: int, end_year: int) -> dict[str, Any]:
        with self.db.session() as session:
            if session is None:
                counts: dict[str, int] = defaultdict(int)
                for node in LOCAL_GRAPH.nodes:
                    if node.get("Node Type") not in {"Song", "Album"}:
                        continue
                    try:
                        year = int(str(node.get("release_date"))[:4])
                    except (TypeError, ValueError):
                        continue
                    if year < start_year or year > end_year:
                        continue
                    genre = node.get("genre")
                    if genre:
                        counts[str(genre)] += 1
                stats = [{"genre": genre, "song_count": count} for genre, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)]
                return {"genres": stats, "start_year": start_year, "end_year": end_year}

            query = """
            MATCH (s:Song)
            WHERE toInteger(s.release_date) >= $start_year
              AND toInteger(s.release_date) <= $end_year
              AND s.genre IS NOT NULL
            RETURN s.genre as genre, count(*) as song_count
            ORDER BY song_count DESC
            """
            result = session.run(query, start_year=start_year, end_year=end_year)
            stats = [{"genre": record["genre"], "song_count": record["song_count"]} for record in result]
            return {"genres": stats, "start_year": start_year, "end_year": end_year}


genre_flow_service = GenreFlowService()
