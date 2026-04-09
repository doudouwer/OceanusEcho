"""
流派演变 (Genre Flow) API 路由
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from ..schemas.models import (
    GenreFlowData, GenreFlowRequest, APIResponse, MetaInfo
)
from ..services.genre_flow_service import genre_flow_service

router = APIRouter(prefix="/analysis", tags=["流派演变 (Genre Flow)"])


@router.get("/genre-flow", response_model=APIResponse)
async def get_genre_flow(
    start_year: int = Query(..., ge=1970, le=2050, description="起始年份"),
    end_year: int = Query(..., ge=1970, le=2050, description="结束年份"),
    metric: str = Query(default="style_edges", description="指标类型: style_edges | genre_mix"),
    source_genre: Optional[str] = Query(None, description="源流派，用于聚焦"),
    limit: int = Query(default=100, ge=1, le=500, description="返回结果上限")
):
    """
    获取流派演变数据

    提供两种可视化模式：
    1. **桑基图 (style_edges)**: 展示流派之间的风格影响流动
       - 边的权重表示从一个流派流向另一个流派的风格影响力
       - 适合展示如 "Oceanus Folk 如何渗透到 Indie Pop"
       - value = 时间窗内 IN_STYLE_OF 从 A 流派艺人到 B 流派艺人的边数

    2. **河流图 (genre_mix)**: 展示流派随时间的数量变化
       - 每条"河流"代表一个流派
       - 河流宽度表示该年份该流派的歌曲数量

    **参数说明**:
    - `start_year` / `end_year`: 时间范围筛选
    - `metric`: 选择可视化模式 (style_edges=桑基图, genre_mix=河流图)
    - `source_genre`: 可选，聚焦特定源流派的传播路径
    - `limit`: 桑基图边的数量上限

    **返回数据结构**:
    - 桑基图: `nodes` (流派列表) + `links` (流动关系)
    - 河流图: `series` (每个流派的时间序列数据)
    """

    # 验证年份范围
    if start_year > end_year:
        raise HTTPException(
            status_code=400,
            detail="start_year 必须小于或等于 end_year"
        )

    # 验证 metric 参数（符合文档要求）
    valid_metrics = ["style_edges", "genre_mix"]
    if metric not in valid_metrics:
        raise HTTPException(
            status_code=400,
            detail=f"无效的 metric 值。可选值: {valid_metrics}"
        )
    
    try:
        if metric == "style_edges":
            # 获取桑基图数据
            data = genre_flow_service.get_sankey_data(
                start_year=start_year,
                end_year=end_year,
                source_genre=source_genre,
                limit=limit
            )
            
            meta = MetaInfo(
                truncated=len(data.links or []) >= limit if data.links else False,
                node_count=len(data.nodes) if data.nodes else 0,
                link_count=len(data.links) if data.links else 0
            )
            
        else:  # genre_mix (河流图)
            # 获取河流图数据
            data = genre_flow_service.get_streamgraph_data(
                start_year=start_year,
                end_year=end_year,
                limit=limit
            )
            
            meta = MetaInfo(
                node_count=len(data.series) if data.series else 0
            )
        
        return APIResponse(data=data, meta=meta)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取流派演变数据失败: {str(e)}"
        )


@router.get("/genre-stats", response_model=APIResponse)
async def get_genre_stats(
    start_year: int = Query(..., ge=1970, le=2050, description="起始年份"),
    end_year: int = Query(..., ge=1970, le=2050, description="结束年份")
):
    """
    获取流派统计信息
    
    返回所有流派的歌曲数量统计，用于：
    - 流派下拉选择器
    - 流派过滤器选项
    """
    
    try:
        stats = genre_flow_service.get_genre_stats(start_year, end_year)
        return APIResponse(data=stats, meta=MetaInfo())
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取流派统计失败: {str(e)}"
        )
