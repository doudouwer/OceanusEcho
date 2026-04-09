from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.deps import get_neo4j_session
from app.schemas.common import ApiResponse
from app.schemas.search import SearchData
from app.services import repository as repo

router = APIRouter(tags=["search"])


@router.get("/search", response_model=ApiResponse[SearchData])
async def get_search(
    q: str = Query("", min_length=0),
    search_type: Literal["person", "song", "all"] = Query("all", alias="type"),
    limit: int = Query(20, ge=1, le=200),
    session=Depends(get_neo4j_session),
) -> ApiResponse[SearchData]:
    data, meta = await repo.fetch_search(session, q, search_type, limit)
    return ApiResponse(data=data, meta=meta)
