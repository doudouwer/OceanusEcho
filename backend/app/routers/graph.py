from typing import Literal

from fastapi import APIRouter, Depends, Path, Query

from app.deps import get_neo4j_session
from app.schemas.common import ApiResponse
from app.schemas.graph import GraphPayload, SubgraphRequest
from app.services import repository as repo

router = APIRouter(prefix="/graph", tags=["graph"])


@router.post("/subgraph", response_model=ApiResponse[GraphPayload])
async def post_subgraph(
    body: SubgraphRequest,
    session=Depends(get_neo4j_session),
) -> ApiResponse[GraphPayload]:
    data, meta = await repo.fetch_subgraph(session, body)
    return ApiResponse(data=data, meta=meta)


@router.get("/expand/{node_id}", response_model=ApiResponse[GraphPayload])
async def get_expand(
    node_id: str = Path(..., description="节点 id（与图数据中的 id 属性一致）或 name"),
    rel_types: str | None = Query(None, description="逗号分隔，如 PERFORMER_OF,IN_STYLE_OF"),
    direction: Literal["out", "in", "both"] = "both",
    limit: int = Query(200, ge=1, le=5000),
    session=Depends(get_neo4j_session),
) -> ApiResponse[GraphPayload]:
    data, meta = await repo.fetch_expand(session, node_id, rel_types, direction, limit)
    return ApiResponse(data=data, meta=meta)
