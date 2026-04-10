from fastapi import APIRouter, HTTPException, Path, Query

from app.schemas.analysis import InfluenceGalaxyData
from app.schemas.graph import GraphPayload, SubgraphRequest
from app.schemas.models import APIResponse, MetaInfo
from app.services.influence_galaxy_service import influence_galaxy_service

router = APIRouter(prefix="/graph", tags=["影响力网络 (Influence Galaxy)"])


@router.post("/subgraph", response_model=APIResponse)
async def post_subgraph(body: SubgraphRequest):
    if body.end_year < body.start_year:
        raise HTTPException(status_code=400, detail="end_year must be >= start_year")
    data = influence_galaxy_service.get_subgraph(
        body.start_year,
        body.end_year,
        body.genres,
        body.seed_person_ids,
        body.rel_types,
        body.limit_nodes,
        body.only_notable_songs,
    )
    return APIResponse(
        data=data,
        meta=MetaInfo(
            node_count=len(data.graph.nodes),
            link_count=len(data.graph.links),
        ),
    )


@router.get("/expand/{node_id}", response_model=APIResponse)
async def get_expand(
    node_id: str = Path(..., description="节点 ID（original_id 或内部 id）或 name"),
    rel_types: str | None = Query(None, description="逗号分隔，如 PERFORMER_OF,IN_STYLE_OF"),
    direction: str = Query("both", pattern="^(out|in|both)$"),
    limit: int = Query(200, ge=1, le=5000),
):
    graph = influence_galaxy_service.expand(node_id, rel_types, direction, limit)
    return APIResponse(
        data=graph,
        meta=MetaInfo(
            node_count=len(graph.nodes),
            link_count=len(graph.links),
        ),
    )
