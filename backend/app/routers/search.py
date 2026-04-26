from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.schemas.common import ApiMeta, ApiResponse
from app.schemas.search import SearchHit, SearchResponseData


router = APIRouter(prefix="/search", tags=["搜索"])


def _public_id(node) -> str:
    raw = node.get("original_id")
    if raw is None:
        raw = node.get("id")
    if raw is not None:
        return str(raw)
    return str(getattr(node, "element_id", ""))


@router.get("", response_model=ApiResponse)
async def get_search(
    request: Request,
    q: str = Query("", min_length=0),
    type: Literal["person", "song", "all"] = Query("all"),
    limit: int = Query(20, ge=1, le=200),
):
    driver = getattr(request.app.state, "neo4j_driver", None)
    if driver is None:
        raise HTTPException(status_code=503, detail="数据库连接不可用")

    if not q.strip():
        return ApiResponse(data=SearchResponseData(results=[], total=0, query=q), meta=ApiMeta(db="connected"))

    qlow = q.strip().lower()
    hits: list[SearchHit] = []

    async with driver.session() as session:
        if type in ("person", "all"):
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
                hits.append(SearchHit(
                    id=_public_id(p),
                    label=str(p.get("name") or ""),
                    type="person",
                    subtitle="Person",
                ))

        if type in ("song", "all") and len(hits) < limit:
            remaining = limit - len(hits)
            res = await session.run(
                """
                MATCH (s:Song)
                WHERE toLower(toString(s.name)) CONTAINS $q
                RETURN s
                LIMIT $lim
                """,
                q=qlow,
                lim=remaining,
            )
            for row in await res.data():
                s = row["s"]
                subtitle_parts = []
                if s.get("release_date"):
                    subtitle_parts.append(str(s.get("release_date")))
                if s.get("genre"):
                    subtitle_parts.append(str(s.get("genre")))
                hits.append(SearchHit(
                    id=_public_id(s),
                    label=str(s.get("name") or ""),
                    type="song",
                    subtitle=" · ".join(subtitle_parts) if subtitle_parts else "Song",
                ))

    return ApiResponse(
        data=SearchResponseData(results=hits[:limit], total=len(hits[:limit]), query=q),
        meta=ApiMeta(db="connected"),
    )
