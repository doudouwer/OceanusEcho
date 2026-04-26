import math
from collections import defaultdict
from collections.abc import Iterable
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.schemas.analysis import (
    CareerSummary,
    CareerTrackData,
    GenreFlowData,
    GenreSankeyLink,
    GenreSankeyNode,
    GenreSeries,
    GenreStreamPoint,
    PersonProfileData,
    PersonProfileMetrics,
    PersonProfileNormalizedRow,
    PersonProfileRow,
    PersonRef,
    WorkItem,
    YearAgg,
)
from app.schemas.common import ApiMeta, ApiResponse


router = APIRouter(prefix="/analysis", tags=["分析视图"])


# ---- 工具函数 ----

def _public_id(node: Any) -> str:
    raw = node.get("original_id")
    if raw is None:
        raw = node.get("id")
    if raw is not None:
        return str(raw)
    return str(getattr(node, "element_id", ""))


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


def _build_meta(**kwargs) -> ApiMeta:
    return ApiMeta(**kwargs)


# ---- Career Arc ----

@router.get("/career-track", response_model=ApiResponse)
async def get_career_track(
    request: Request,
    person_id: Optional[str] = Query(None, description="艺人 ID（original_id 或内部 id）"),
    person_name: Optional[str] = Query(None, description="艺人姓名"),
    start_year: int = Query(2023, ge=1900, le=2200),
    end_year: int = Query(2040, ge=1900, le=2200),
):
    if end_year < start_year:
        raise HTTPException(status_code=400, detail="end_year must be >= start_year")
    if not person_id and not person_name:
        raise HTTPException(status_code=400, detail="需要提供 person_id 或 person_name")

    driver = getattr(request.app.state, "neo4j_driver", None)
    if driver is None:
        raise HTTPException(status_code=503, detail="数据库连接不可用")

    async with driver.session() as session:
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
        result = await session.run(cypher, pid=person_id, pname=person_name, sy=start_year, ey=end_year)
        rows = await result.data()
        if not rows:
            raise HTTPException(status_code=404, detail="未找到该艺人或时间窗内无作品")

        p0 = rows[0]["p"]
        person = PersonRef(id=_public_id(p0), name=str(p0.get("name") or ""))

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
                    song_id=_public_id(s),
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

        total_works = len(works)
        first_release_year = min(by_year.keys()) if by_year else None
        notable_years = [y for y, v in by_year.items() if v["notable_count"] > 0]
        first_notable_year = min(notable_years) if notable_years else None
        peak_year = max(by_year.items(), key=lambda x: x[1]["song_count"])[0] if by_year else None
        fame_gap_years = peak_year - first_notable_year if (first_notable_year and peak_year) else None
        active_span_years = (max(by_year.keys()) - min(by_year.keys()) + 1) if by_year else 0

        summary = CareerSummary(
            first_release_year=first_release_year,
            first_notable_year=first_notable_year,
            fame_gap_years=fame_gap_years,
            peak_year=peak_year,
            active_span_years=active_span_years,
            total_works=total_works,
        )

        return ApiResponse(
            data=CareerTrackData(person=person, summary=summary, by_year=agg, works=works),
            meta=_build_meta(db="connected"),
        )


# ---- Genre Flow ----

@router.get("/genre-flow", response_model=ApiResponse)
async def get_genre_flow(
    request: Request,
    start_year: int = Query(2023, ge=1900, le=2200),
    end_year: int = Query(2040, ge=1900, le=2200),
    metric: str = Query("style_edges", description="style_edges | genre_mix"),
    source_genre: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    if end_year < start_year:
        raise HTTPException(status_code=400, detail="end_year must be >= start_year")

    driver = getattr(request.app.state, "neo4j_driver", None)
    if driver is None:
        raise HTTPException(status_code=503, detail="数据库连接不可用")

    async with driver.session() as session:
        if metric == "genre_mix":
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
            return ApiResponse(
                data=GenreFlowData(series=series),
                meta=_build_meta(node_count=len(series), db="connected"),
            )

        cypher = """
        MATCH (song:Song)-[:IN_STYLE_OF]->(style_source)
        WHERE toInteger(song.release_date) >= $sy
          AND toInteger(song.release_date) <= $ey
          AND song.genre IS NOT NULL
          AND (
            (style_source:Song AND style_source.genre IS NOT NULL)
            OR (style_source:Album AND style_source.genre IS NOT NULL)
            OR (style_source:Person AND style_source.inferred_genre IS NOT NULL)
            OR (style_source:MusicalGroup AND style_source.inferred_genre IS NOT NULL)
          )
          AND song.genre <> coalesce(style_source.genre, style_source.inferred_genre)
          AND ($sg IS NULL OR song.genre = $sg)
        WITH song.genre as source_genre,
             coalesce(style_source.genre, style_source.inferred_genre) as target_genre,
             count(*) as flow_count
        RETURN source_genre, target_genre, flow_count
        ORDER BY flow_count DESC
        LIMIT $lim
        """
        result = await session.run(cypher, sy=start_year, ey=end_year, sg=source_genre, lim=limit)
        rows = await result.data()
        nodes_set: set[str] = set()
        links: list[GenreSankeyLink] = []
        for row in rows:
            s, t, v = row["source_genre"], row["target_genre"], float(row["flow_count"])
            nodes_set.add(s)
            nodes_set.add(t)
            links.append(GenreSankeyLink(source=s, target=t, value=v))
        nodes = [GenreSankeyNode(id=x) for x in sorted(nodes_set)]
        return ApiResponse(
            data=GenreFlowData(nodes=nodes, links=links),
            meta=_build_meta(
                truncated=len(links) >= limit,
                node_count=len(nodes),
                link_count=len(links),
                db="connected",
            ),
        )


@router.get("/genre-stats", response_model=ApiResponse)
async def get_genre_stats(
    request: Request,
    start_year: int = Query(2023, ge=1900, le=2200),
    end_year: int = Query(2040, ge=1900, le=2200),
):
    if end_year < start_year:
        raise HTTPException(status_code=400, detail="end_year must be >= start_year")

    driver = getattr(request.app.state, "neo4j_driver", None)
    if driver is None:
        raise HTTPException(status_code=503, detail="数据库连接不可用")

    async with driver.session() as session:
        cypher = """
        MATCH (s:Song)
        WHERE toInteger(s.release_date) >= $sy
          AND toInteger(s.release_date) <= $ey
          AND s.genre IS NOT NULL
        RETURN s.genre as genre, count(*) as song_count
        ORDER BY song_count DESC
        """
        result = await session.run(cypher, sy=start_year, ey=end_year)
        rows = await result.data()
        genres = [{"genre": r["genre"], "song_count": r["song_count"]} for r in rows]
        return ApiResponse(
            data={"genres": genres, "start_year": start_year, "end_year": end_year},
            meta=_build_meta(db="connected"),
        )


# ---- Person Profile ----

@router.get("/person-profile", response_model=ApiResponse)
async def get_person_profile(
    request: Request,
    person_ids: str = Query(..., description="艺人 ID，多个用逗号分隔"),
    start_year: Optional[int] = Query(None, ge=1900, le=2200),
    end_year: Optional[int] = Query(None, ge=1900, le=2200),
    normalized: bool = Query(
        True,
        description="是否以锚点艺人为基准做归一化（锚点固定为 ID 列表中的第一位）",
    ),
):
    id_list = [pid.strip() for pid in person_ids.split(",") if pid.strip()]
    if not id_list:
        raise HTTPException(status_code=400, detail="至少需要一个艺人 ID")
    if len(id_list) > 20:
        raise HTTPException(status_code=400, detail="最多支持 20 个艺人")
    if start_year and end_year and start_year > end_year:
        raise HTTPException(status_code=400, detail="start_year 必须 <= end_year")

    driver = getattr(request.app.state, "neo4j_driver", None)
    if driver is None:
        raise HTTPException(status_code=503, detail="数据库连接不可用")

    sy = start_year if start_year is not None else 0
    ey = end_year if end_year is not None else 9999

    dims = [
        "song_count",
        "notable_rate",
        "active_years",
        "unique_collaborators",
        "genre_entropy",
        "degree",
        "pagerank",
    ]
    profiles: list[PersonProfileRow] = []

    all_rel_types = [
        "PERFORMER_OF", "COMPOSER_OF", "PRODUCER_OF",
        "LYRICIST_OF", "IN_STYLE_OF", "MEMBER_OF",
        "SIGNED_TO", "INTERPOLATES_FROM",
    ]

    async with driver.session() as session:
        for pid in id_list:
            cypher = f"""
            MATCH (p:Person)
            WHERE toString(p.original_id) = $pid OR toString(p.id) = $pid OR p.name = $pid

            // 1) 时间窗内的歌曲（含所有贡献关系）
            OPTIONAL MATCH (p)-[r1]-(s:Song)
            WHERE type(r1) IN $all_rel
              AND toInteger(trim(toString(s.release_date))) >= $sy
              AND toInteger(trim(toString(s.release_date))) <= $ey
            WITH p, collect(DISTINCT s) AS songs

            // 2) 时间窗内的合作者（含所有贡献关系）
            UNWIND songs AS song
            OPTIONAL MATCH (other:Person)-[r2]-(song)
            WHERE other <> p AND type(r2) IN $all_rel
            WITH p, songs, collect(DISTINCT other) AS others

            // 3) 全局度数（所有关系、所有时间）
            OPTIONAL MATCH (p)-[r3]-()
            WHERE type(r3) IN $all_rel
            WITH p, songs, others,
                 count(DISTINCT r3) AS raw_degree

            // 4) 近似 PageRank：2 跳可达的不同 Person 节点数
            OPTIONAL MATCH (p)-[:PERFORMER_OF|COMPOSER_OF|PRODUCER_OF|LYRICIST_OF|MEMBER_OF|SIGNED_TO|IN_STYLE_OF|INTERPOLATES_FROM*1..2]-(neighbor)
            WHERE neighbor:Person
            WITH p, songs, others, raw_degree,
                 count(DISTINCT neighbor) AS pagerank_proxy

            RETURN p, songs, others, raw_degree, pagerank_proxy
            """
            result = await session.run(
                cypher,
                pid=pid,
                sy=sy,
                ey=ey,
                all_rel=all_rel_types,
            )
            row = await result.single()
            if row is None:
                continue
            p = row["p"]
            songs = [x for x in row["songs"] if x is not None]
            others = {_public_id(o) for o in row["others"] if o is not None}
            others.discard(_public_id(p))

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
                degree=int(row["raw_degree"]) if row["raw_degree"] else 0,
                pagerank=round(float(row["pagerank_proxy"]), 4) if row["pagerank_proxy"] else 0.0,
            )
            profiles.append(PersonProfileRow(
                person_id=_public_id(p),
                name=str(p.get("name") or ""),
                metrics=metrics,
            ))

    if not profiles:
        raise HTTPException(status_code=404, detail="未找到指定的艺人")

    if normalized:
        anchor = profiles[0]
        anchor_vals = {dim: getattr(anchor.metrics, dim, 0) for dim in dims}

        normalized_profiles = []
        for p in profiles:
            norm_metrics = {}
            raw_dict = {}
            for dim in dims:
                raw = getattr(p.metrics, dim, 0)
                raw_dict[dim] = raw
                anchor_v = anchor_vals[dim]
                if anchor_v > 0:
                    norm_metrics[dim] = round(raw / anchor_v, 4)
                else:
                    norm_metrics[dim] = 0.0
            normalized_profiles.append(PersonProfileNormalizedRow(
                person_id=p.person_id,
                name=p.name,
                metrics=norm_metrics,
                raw_metrics=raw_dict,
            ))
        return ApiResponse(
            data={
                "profiles": normalized_profiles,
                "dimensions": dims,
                "anchor_id": anchor.person_id,
                "anchor_name": anchor.name,
                "normalization": {"type": "ratio-to-anchor"},
            },
            meta=_build_meta(total_hint=len(id_list), db="connected"),
        )

    return ApiResponse(
        data=PersonProfileData(profiles=profiles, dimensions=dims),
        meta=_build_meta(total_hint=len(id_list), db="connected"),
    )
