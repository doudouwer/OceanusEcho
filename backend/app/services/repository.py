import math
from collections import defaultdict
from collections.abc import Iterable

from neo4j import AsyncSession

from app.constants import DEFAULT_REL_TYPES
from app.schemas.analysis import (
    CareerTrackData,
    GenreFlowData,
    GenreSankeyLink,
    GenreSankeyNode,
    GenreSeries,
    GenreStreamPoint,
    PersonProfileData,
    PersonProfileMetrics,
    PersonProfileRow,
    PersonRef,
    WorkItem,
    YearAgg,
)
from app.schemas.common import ApiMeta
from app.schemas.graph import GraphLink, GraphNode, GraphPayload, SubgraphRequest
from app.schemas.search import SearchData, SearchHit
from app.services.neo4j_serialize import graph_link_from_neo, graph_node_from_neo, node_public_id


def _map_api_rel_types(requested: list[str]) -> list[str]:
    if not requested:
        return [DEFAULT_REL_TYPES["PERFORMER_OF"], DEFAULT_REL_TYPES["IN_STYLE_OF"]]
    out: list[str] = []
    for r in requested:
        key = r.strip().upper()
        out.append(DEFAULT_REL_TYPES.get(key, r))
    return list(dict.fromkeys(out))


async def fetch_subgraph(session: AsyncSession | None, body: SubgraphRequest) -> tuple[GraphPayload, ApiMeta]:
    meta = ApiMeta(db="offline" if session is None else "connected")
    if session is None:
        return GraphPayload(nodes=[], links=[]), meta

    seed = [str(x) for x in body.seed_person_ids]
    genres = body.genres
    lim = body.limit_nodes
    notable_filter = "AND coalesce(s.notable, false) = true" if body.only_notable_songs else ""

    cypher = f"""
    MATCH (p:Person)-[r:PerformerOf]->(s:Song)
    WHERE toInteger(trim(toString(s.release_date))) >= $sy
      AND toInteger(trim(toString(s.release_date))) <= $ey
      {notable_filter}
      AND (size($genres) = 0 OR s.genre IN $genres)
      AND (size($seed) = 0 OR toString(p.id) IN $seed OR p.name IN $seed)
    RETURN p, r, s
    LIMIT $lim
    """
    result = await session.run(
        cypher,
        sy=body.start_year,
        ey=body.end_year,
        genres=genres,
        seed=seed,
        lim=lim,
    )
    records = await result.data()

    nodes: dict[str, GraphNode] = {}
    links: list[GraphLink] = []

    for row in records:
        p, r, s = row["p"], row["r"], row["s"]
        pn = graph_node_from_neo(p)
        sn = graph_node_from_neo(s)
        nodes[pn.id] = pn
        nodes[sn.id] = sn
        links.append(graph_link_from_neo(pn.id, sn.id, r))

    meta.node_count = len(nodes)
    meta.link_count = len(links)
    meta.truncated = len(records) >= lim
    return GraphPayload(nodes=list(nodes.values()), links=links), meta


async def fetch_expand(
    session: AsyncSession | None,
    node_id: str,
    rel_types: str | None,
    direction: str,
    limit: int,
) -> tuple[GraphPayload, ApiMeta]:
    meta = ApiMeta(db="offline" if session is None else "connected")
    if session is None:
        return GraphPayload(nodes=[], links=[]), meta

    types = _map_api_rel_types([x.strip() for x in rel_types.split(",")] if rel_types else [])

    # direction: out | in | both — 用 string 模板仅允许白名单类型，避免注入
    if direction == "out":
        pattern = "(n)-[r]->(m)"
    elif direction == "in":
        pattern = "(n)<-[r]-(m)"
    else:
        pattern = "(n)-[r]-(m)"

    cypher = f"""
    MATCH (n)
    WHERE toString(n.id) = $nid OR n.name = $nid
    WITH n LIMIT 1
    MATCH {pattern}
    WHERE type(r) IN $types
    RETURN n, r, m
    LIMIT $lim
    """
    result = await session.run(cypher, nid=node_id, types=types, lim=limit)
    records = await result.data()

    nodes: dict[str, GraphNode] = {}
    links: list[GraphLink] = []

    for row in records:
        n, r, m = row["n"], row["r"], row["m"]
        nn = graph_node_from_neo(n)
        mn = graph_node_from_neo(m)
        nodes[nn.id] = nn
        nodes[mn.id] = mn
        sid = node_public_id(r.start_node)
        tid = node_public_id(r.end_node)
        links.append(graph_link_from_neo(sid, tid, r))

    meta.node_count = len(nodes)
    meta.link_count = len(links)
    meta.truncated = len(records) >= limit
    return GraphPayload(nodes=list(nodes.values()), links=links), meta


async def fetch_career_track(
    session: AsyncSession | None,
    person_id: str | None,
    person_name: str | None,
    start_year: int,
    end_year: int,
) -> tuple[CareerTrackData | None, ApiMeta]:
    meta = ApiMeta(db="offline" if session is None else "connected")
    empty_person = PersonRef(id=person_id or "", name=person_name or person_id or "未指定")

    if session is None:
        return CareerTrackData(person=empty_person, by_year=[], works=[]), meta

    cypher = """
    MATCH (p:Person)
    WHERE ($pid IS NULL OR toString(p.id) = $pid) AND ($pname IS NULL OR p.name = $pname)
    MATCH (p)-[:PerformerOf]->(s:Song)
    WHERE toInteger(trim(toString(s.release_date))) >= $sy
      AND toInteger(trim(toString(s.release_date))) <= $ey
    RETURN p, s
    ORDER BY toInteger(trim(toString(s.release_date))), s.name
    """
    result = await session.run(
        cypher,
        pid=person_id,
        pname=person_name,
        sy=start_year,
        ey=end_year,
    )
    rows = await result.data()
    if not rows:
        return None, meta

    p0 = rows[0]["p"]
    person = PersonRef(id=node_public_id(p0), name=str(p0.get("name") or ""))

    by_year: dict[int, dict] = defaultdict(lambda: {"song_count": 0, "notable_count": 0, "genres": set()})
    works: list[WorkItem] = []

    for row in rows:
        s = row["s"]
        y = int(str(s.get("release_date", "0")).strip()[:4])
        if y < start_year or y > end_year:
            continue
        g = s.get("genre")
        by_year[y]["song_count"] += 1
        if bool(s.get("notable")):
            by_year[y]["notable_count"] += 1
        if g:
            by_year[y]["genres"].add(str(g))
        works.append(
            WorkItem(
                song_id=node_public_id(s),
                title=str(s.get("name") or ""),
                release_date=str(s.get("release_date") or ""),
                notable=bool(s.get("notable")),
                genre=str(g) if g is not None else None,
            )
        )

    agg = [
        YearAgg(
            year=y,
            song_count=v["song_count"],
            notable_count=v["notable_count"],
            genres=sorted(v["genres"]),
        )
        for y, v in sorted(by_year.items())
    ]

    return CareerTrackData(person=person, by_year=agg, works=works), meta


async def fetch_genre_flow(
    session: AsyncSession | None,
    start_year: int,
    end_year: int,
    view: str,
    metric: str,
    source_genre: str | None,
) -> tuple[GenreFlowData, ApiMeta]:
    meta = ApiMeta(db="offline" if session is None else "connected")
    if session is None:
        if view == "stream":
            return GenreFlowData(series=[]), meta
        return GenreFlowData(nodes=[], links=[]), meta

    if view == "stream":
        cypher = """
        MATCH (s:Song)
        WHERE toInteger(trim(toString(s.release_date))) >= $sy
          AND toInteger(trim(toString(s.release_date))) <= $ey
          AND s.genre IS NOT NULL
        RETURN toInteger(trim(toString(s.release_date))) AS year, s.genre AS genre, count(*) AS value
        ORDER BY year, genre
        """
        result = await session.run(cypher, sy=start_year, ey=end_year)
        rows = await result.data()
        bucket: dict[str, dict[int, float]] = defaultdict(lambda: defaultdict(float))
        for row in rows:
            bucket[row["genre"]][int(row["year"])] += float(row["value"])
        series = [
            GenreSeries(
                genre=g,
                points=[GenreStreamPoint(year=y, value=v) for y, v in sorted(ys.items())],
            )
            for g, ys in bucket.items()
        ]
        return GenreFlowData(series=series), meta

    # sankey：同一 Person 上两首不同流派歌曲经 InStyleOf 共现（近似「风格影响」下的流派桥接）
    _ = metric
    cypher = """
    MATCH (sa:Song)-[:InStyleOf]->(hub:Person)<-[:InStyleOf]-(sb:Song)
    WHERE sa.genre IS NOT NULL AND sb.genre IS NOT NULL AND sa.genre <> sb.genre
      AND toInteger(trim(toString(sa.release_date))) >= $sy
      AND toInteger(trim(toString(sa.release_date))) <= $ey
      AND toInteger(trim(toString(sb.release_date))) >= $sy
      AND toInteger(trim(toString(sb.release_date))) <= $ey
      AND ($sg IS NULL OR sa.genre = $sg OR sb.genre = $sg)
    RETURN sa.genre AS source, sb.genre AS target, count(*) AS value
    ORDER BY value DESC
    LIMIT 120
    """
    result = await session.run(cypher, sy=start_year, ey=end_year, sg=source_genre)
    rows = await result.data()
    nodes_set: set[str] = set()
    links: list[GenreSankeyLink] = []
    for row in rows:
        s, t, v = row["source"], row["target"], float(row["value"])
        nodes_set.add(s)
        nodes_set.add(t)
        links.append(GenreSankeyLink(source=s, target=t, value=v))
    nodes = [GenreSankeyNode(id=x) for x in sorted(nodes_set)]
    return GenreFlowData(nodes=nodes, links=links), meta


def _entropy(counts: Iterable[int]) -> float:
    total = sum(counts)
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts:
        if c <= 0:
            continue
        p = c / total
        h -= p * math.log(p + 1e-12, 2)
    return round(h, 4)


async def fetch_person_profiles(
    session: AsyncSession | None,
    person_ids: list[str],
    start_year: int,
    end_year: int,
) -> tuple[PersonProfileData, ApiMeta]:
    dims = [
        "song_count",
        "notable_rate",
        "active_years",
        "unique_collaborators",
        "genre_entropy",
        "degree",
        "pagerank",
    ]
    meta = ApiMeta(db="offline" if session is None else "connected")
    if session is None or not person_ids:
        return PersonProfileData(profiles=[], dimensions=dims), meta

    cypher = """
    MATCH (p:Person)
    WHERE toString(p.id) = $pid OR p.name = $pid
    OPTIONAL MATCH (p)-[:PerformerOf]->(s:Song)
    WHERE toInteger(trim(toString(s.release_date))) >= $sy
      AND toInteger(trim(toString(s.release_date))) <= $ey
    OPTIONAL MATCH (other:Person)-[:PerformerOf]->(s)
    WHERE other <> p
    RETURN p, collect(DISTINCT s) AS songs, collect(DISTINCT other) AS others
    """

    profiles: list[PersonProfileRow] = []
    for pid in person_ids:
        result = await session.run(cypher, pid=pid, sy=start_year, ey=end_year)
        row = await result.single()
        if row is None:
            continue
        p = row["p"]
        songs = [x for x in row["songs"] if x is not None]
        others = {node_public_id(o) for o in row["others"] if o is not None}
        others.discard(node_public_id(p))

        genre_counts: dict[str, int] = defaultdict(int)
        notable_n = 0
        years: set[int] = set()
        for s in songs:
            if s.get("genre"):
                genre_counts[str(s["genre"])] += 1
            if bool(s.get("notable")):
                notable_n += 1
            try:
                years.add(int(str(s.get("release_date", "0")).strip()[:4]))
            except ValueError:
                pass

        n_songs = len(songs)
        metrics = PersonProfileMetrics(
            song_count=n_songs,
            notable_rate=round(notable_n / n_songs, 4) if n_songs else 0.0,
            active_years=len(years),
            unique_collaborators=len(others),
            genre_entropy=_entropy(genre_counts.values()),
            degree=n_songs,
            pagerank=0.0,
        )
        profiles.append(
            PersonProfileRow(
                person_id=node_public_id(p),
                name=str(p.get("name") or ""),
                metrics=metrics,
            )
        )

    return PersonProfileData(profiles=profiles, dimensions=dims), meta


async def fetch_search(
    session: AsyncSession | None,
    q: str,
    type_: str,
    limit: int,
) -> tuple[SearchData, ApiMeta]:
    meta = ApiMeta(db="offline" if session is None else "connected")
    if session is None or not q.strip():
        return SearchData(hits=[]), meta

    qlow = q.strip().lower()
    hits: list[SearchHit] = []

    async def run_person() -> None:
        res = await session.run(
            """
            MATCH (p:Person)
            WHERE toLower(toString(p.name)) CONTAINS $q
            RETURN p
            LIMIT $lim
            """,
            q=qlow,
            lim=limit,
        )
        for row in await res.data():
            p = row["p"]
            hits.append(
                SearchHit(
                    id=node_public_id(p),
                    label="Person",
                    subtitle=str(p.get("name")),
                )
            )

    async def run_song() -> None:
        res = await session.run(
            """
            MATCH (s:Song)
            WHERE toLower(toString(s.name)) CONTAINS $q
            RETURN s
            LIMIT $lim
            """,
            q=qlow,
            lim=limit,
        )
        for row in await res.data():
            s = row["s"]
            hits.append(
                SearchHit(
                    id=node_public_id(s),
                    label="Song",
                    subtitle=f"{s.get('release_date', '')} · {s.get('genre', '')}",
                )
            )

    if type_ in ("person", "all"):
        await run_person()
    if type_ in ("song", "all") and len(hits) < limit:
        await run_song()

    return SearchData(hits=hits[:limit]), meta
