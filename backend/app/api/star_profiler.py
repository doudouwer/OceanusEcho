"""
艺人画像 (Star Profiler) API 路由
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from ..schemas.models import (
    PersonProfileData, APIResponse, MetaInfo
)
from ..services.star_profiler_service import star_profiler_service

router = APIRouter(prefix="/analysis", tags=["艺人画像 (Star Profiler)"])


@router.get("/person-profile", response_model=APIResponse)
async def get_person_profile(
    person_ids: str = Query(..., description="艺人 ID，多个用逗号分隔"),
    start_year: Optional[int] = Query(None, ge=1970, le=2050, description="起始年份（可选）"),
    end_year: Optional[int] = Query(None, ge=1970, le=2050, description="结束年份（可选）"),
    normalized: bool = Query(default=False, description="是否返回归一化数据")
):
    """
    获取艺人画像数据
    
    用于雷达图可视化，展示艺人的多维度特征：
    
    **指标维度**:
    - `song_count`: 歌曲数量
    - `notable_rate`: 代表作比例
    - `active_years`: 活跃年数
    - `unique_collaborators`: 独立合作者数
    - `genre_entropy`: 流派多样性（信息熵）
    - `degree`: 图度数（连接数）
    - `pagerank`: PageRank 中心性
    
    **参数说明**:
    - `person_ids`: 艺人 ID 列表，最多 20 个
    - `start_year` / `end_year`: 时间范围筛选（可选）
    - `normalized`: 是否返回归一化数据（默认 False）
    
    **返回数据**:
    - `profiles`: 每个艺人的画像数据
    - `dimensions`: 包含的指标维度列表
    - `metrics_normalized`: 仅当 normalized=True 时返回
    """
    
    # 解析 person_ids
    try:
        person_id_list = [pid.strip() for pid in person_ids.split(",") if pid.strip()]
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="person_ids 格式错误，请使用逗号分隔的 ID 列表"
        )
    
    # 验证数量限制
    if len(person_id_list) > 20:
        raise HTTPException(
            status_code=400,
            detail="最多支持 20 个艺人同时查询"
        )
    
    if len(person_id_list) == 0:
        raise HTTPException(
            status_code=400,
            detail="至少需要提供一个艺人 ID"
        )
    
    # 验证年份范围
    if start_year and end_year and start_year > end_year:
        raise HTTPException(
            status_code=400,
            detail="start_year 必须小于或等于 end_year"
        )
    
    try:
        if normalized:
            # 返回归一化数据
            normalized_data = star_profiler_service.get_normalized_profiles(
                person_ids=person_id_list,
                start_year=start_year,
                end_year=end_year
            )
            
            return APIResponse(
                data=normalized_data,
                meta=MetaInfo(
                    total_hint=len(person_id_list)
                )
            )
        else:
            # 返回原始数据
            profile_data = star_profiler_service.get_person_profiles(
                person_ids=person_id_list,
                start_year=start_year,
                end_year=end_year
            )
            
            return APIResponse(
                data=profile_data,
                meta=MetaInfo(
                    total_hint=len(person_id_list)
                )
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取艺人画像失败: {str(e)}"
        )


@router.get("/person-profile/{person_id}", response_model=APIResponse)
async def get_single_person_profile(
    person_id: str,
    start_year: Optional[int] = Query(None, ge=1970, le=2050, description="起始年份（可选）"),
    end_year: Optional[int] = Query(None, ge=1970, le=2050, description="结束年份（可选）")
):
    """
    获取单个艺人画像
    
    便捷端点，用于获取单个艺人的详细信息
    """
    
    # 验证年份范围
    if start_year and end_year and start_year > end_year:
        raise HTTPException(
            status_code=400,
            detail="start_year 必须小于或等于 end_year"
        )
    
    try:
        profile = star_profiler_service.get_person_profile(
            person_id=person_id,
            start_year=start_year,
            end_year=end_year
        )
        
        return APIResponse(
            data={"profile": profile},
            meta=MetaInfo()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取艺人画像失败: {str(e)}"
        )
