from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.core.database import get_neo4j_connection
from app.schemas.analysis import CareerSummary, CareerTrackData, PersonRef, WorkItem, YearAgg
from app.services.local_graph import load_local_graph
from app.services.neo4j_serialize import node_public_id


LOCAL_GRAPH = load_local_graph()


def _build_summary(by_year: list[YearAgg], works_len: int) -> CareerSummary | None:
    if not by_year:
        return None
    first_release_year = by_year[0].year
    first_notable_year = next((item.year for item in by_year if item.notable_count > 0), None)
    return CareerSummary(
        first_release_year=first_release_year,
        first_notable_year=first_notable_year,
        fame_gap_years=(first_notable_year - first_release_year) if first_notable_year is not None else None,
        peak_year=max(by_year, key=lambda item: (item.song_count, item.year)).year,
        active_span_years=(by_year[-1].year - by_year[0].year + 1) if len(by_year) > 1 else 1,
        total_works=works_len,
    )


class CareerArcService:
    def __init__(self) -> None:
        self.db = get_neo4j_connection()

    def get_career_track(
        self,
        person_id: str | None,
        person_name: str | None,
        start_year: int,
        end_year: int,
    ) -> CareerTrackData | None:
        with self.db.session() as session:
            if session is None:
                payload = LOCAL_GRAPH.career_track(person_id, person_name, start_year, end_year)
                if payload is None:
                    return None
                return CareerTrackData(
                    person=PersonRef(**payload["person"]),
                    summary=CareerSummary(**payload["summary"]) if payload.get("summary") else None,
                    by_year=[YearAgg(**row) for row in payload["by_year"]],
                    works=[WorkItem(**row) for row in payload["works"]],
                )

            cypher = """
            MATCH (p:Person)
            WHERE ($pid IS NULL OR toString(p.original_id) = $pid OR toString(p.id) = $pid)
              AND ($pname IS NULL OR p.name = $pname)
            MATCH (p)-[:PERFORMER_OF]->(s:Song)
            WHERE toInteger(trim(toString(s.release_date))) >= $sy
              AND toInteger(trim(toString(s.release_date))) <= $ey
            RETURN p, s
            ORDER BY toInteger(trim(toString(s.release_date))), s.name
            """
            rows = list(session.run(cypher, pid=person_id, pname=person_name, sy=start_year, ey=end_year))
            if not rows:
                return None

            p0 = rows[0]["p"]
            person = PersonRef(id=node_public_id(p0), name=str(p0.get("name") or ""))
            by_year: dict[int, dict[str, Any]] = defaultdict(lambda: {"song_count": 0, "notable_count": 0, "genres": set()})
            works: list[WorkItem] = []

            for row in rows:
                s = row["s"]
                try:
                    year = int(str(s.get("release_date", "0")).strip()[:4])
                except ValueError:
                    continue
                if year < start_year or year > end_year:
                    continue
                genre = s.get("genre")
                by_year[year]["song_count"] += 1
                by_year[year]["notable_count"] += int(bool(s.get("notable")))
                if genre:
                    by_year[year]["genres"].add(str(genre))
                works.append(
                    WorkItem(
                        song_id=node_public_id(s),
                        title=str(s.get("name") or ""),
                        release_date=str(s.get("release_date") or ""),
                        notable=bool(s.get("notable")),
                        genre=str(genre) if genre is not None else None,
                    )
                )

            agg = [
                YearAgg(
                    year=year,
                    song_count=item["song_count"],
                    notable_count=item["notable_count"],
                    genres=sorted(item["genres"]),
                )
                for year, item in sorted(by_year.items())
            ]
            return CareerTrackData(person=person, summary=_build_summary(agg, len(works)), by_year=agg, works=works)


career_arc_service = CareerArcService()
