from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import get_neo4j_session
from app.schemas.analysis import CareerTrackData, GenreFlowData, PersonProfileData
from app.schemas.common import ApiResponse
from app.services import repository as repo

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/career-track", response_model=ApiResponse[CareerTrackData])
async def get_career_track(
    person_id: Optional[str] = None,
    person_name: Optional[str] = None,
    start_year: int = Query(2023, ge=1900, le=2200),
    end_year: int = Query(2040, ge=1900, le=2200),
    session=Depends(get_neo4j_session),
) -> ApiResponse[CareerTrackData]:
    if end_year < start_year:
        raise HTTPException(status_code=400, detail="end_year must be >= start_year")
    if not person_id and not person_name:
        raise HTTPException(status_code=400, detail="需要提供 person_id 或 person_name")

    data, meta = await repo.fetch_career_track(session, person_id, person_name, start_year, end_year)
    if data is None:
        raise HTTPException(status_code=404, detail="未找到该艺人或时间窗内无作品")
    return ApiResponse(data=data, meta=meta)


@router.get("/genre-flow", response_model=ApiResponse[GenreFlowData])
async def get_genre_flow(
    start_year: int = Query(2023, ge=1900, le=2200),
    end_year: int = Query(2040, ge=1900, le=2200),
    view: Literal["sankey", "stream"] = "sankey",
    metric: str = Query("style_edges", description="预留：不同统计口径"),
    source_genre: Optional[str] = None,
    session=Depends(get_neo4j_session),
) -> ApiResponse[GenreFlowData]:
    if end_year < start_year:
        raise HTTPException(status_code=400, detail="end_year must be >= start_year")
    data, meta = await repo.fetch_genre_flow(session, start_year, end_year, view, metric, source_genre)
    return ApiResponse(data=data, meta=meta)


@router.get("/person-profile", response_model=ApiResponse[PersonProfileData])
async def get_person_profile(
    person_ids: Annotated[list[str], Query(description="可重复传参，如 ?person_ids=1&person_ids=2")],
    start_year: int = Query(2023, ge=1900, le=2200),
    end_year: int = Query(2040, ge=1900, le=2200),
    session=Depends(get_neo4j_session),
) -> ApiResponse[PersonProfileData]:
    if end_year < start_year:
        raise HTTPException(status_code=400, detail="end_year must be >= start_year")
    data, meta = await repo.fetch_person_profiles(session, person_ids, start_year, end_year)
    return ApiResponse(data=data, meta=meta)
