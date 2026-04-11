from fastapi import APIRouter, HTTPException, Query

from app.schemas.analysis import CareerTrackData
from app.schemas.models import APIResponse, MetaInfo
from app.services.career_arc_service import career_arc_service

router = APIRouter(prefix="/analysis", tags=["职业时轴 (Career Arc)"])


@router.get("/career-track", response_model=APIResponse)
async def get_career_track(
    person_id: str | None = Query(None, description="艺人 ID（original_id 或内部 id）"),
    person_name: str | None = Query(None, description="艺人姓名"),
    start_year: int = Query(2023, ge=1900, le=2200, description="起始年份"),
    end_year: int = Query(2040, ge=1900, le=2200, description="结束年份"),
):
    if end_year < start_year:
        raise HTTPException(status_code=400, detail="end_year must be >= start_year")
    if not person_id and not person_name:
        raise HTTPException(status_code=400, detail="需要提供 person_id 或 person_name")

    data = career_arc_service.get_career_track(person_id, person_name, start_year, end_year)
    if data is None:
        raise HTTPException(status_code=404, detail="未找到该艺人或时间窗内无作品")

    return APIResponse(data=data, meta=MetaInfo())
