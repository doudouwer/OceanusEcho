"""
搜索 API 路由
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from ..schemas.models import SearchResponse, SearchResult
from ..core.database import get_neo4j_connection

router = APIRouter(prefix="/search", tags=["搜索"])


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, max_length=100, description="搜索关键词"),
    type: str = Query(default="all", description="搜索类型: person | song | all"),
    limit: int = Query(default=20, ge=1, le=100, description="返回结果上限")
):
    """
    全局搜索 Person 或 Song
    
    支持模糊搜索，返回匹配的艺人或歌曲列表。
    
    **参数说明**:
    - `q`: 搜索关键词
    - `type`: 搜索类型 (person / song / all)
    - `limit`: 返回结果数量上限
    
    **返回数据**:
    - `results`: 匹配结果列表
    - `total`: 总匹配数
    - `query`: 原始查询词
    """
    
    # 验证 type 参数
    valid_types = ["person", "song", "all"]
    if type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"无效的 type 值。可选值: {valid_types}"
        )
    
    db = get_neo4j_connection()
    
    try:
        results = []
        total = 0
        
        with db.session() as session:
            if type in ["person", "all"]:
                # 搜索 Person
                person_query = """
                MATCH (p:Person)
                WHERE p.name CONTAINS $keyword OR p.stage_name CONTAINS $keyword
                RETURN p.original_id as id, p.name as name, 'person' as type,
                       p.stage_name as stage_name
                LIMIT $limit
                """
                person_result = session.run(person_query, keyword=q, limit=limit)
                
                for record in person_result:
                    results.append(SearchResult(
                        id=str(record["id"]),
                        label=record["stage_name"] or record["name"],
                        type="person",
                        subtitle=f"艺人 | {record['name']}" if record.get("stage_name") else None
                    ))
                
                total += len(results)
            
            if type in ["song", "all"]:
                # 搜索 Song
                song_query = """
                MATCH (s:Song)
                WHERE s.name CONTAINS $keyword
                RETURN s.original_id as id, s.name as name, s.genre as genre,
                       s.release_date as year, s.notable as notable, 'song' as type
                LIMIT $limit
                """
                song_result = session.run(song_query, keyword=q, limit=limit)
                
                for record in song_result:
                    notable_mark = "★" if record.get("notable") else ""
                    genre = record.get("genre") or ""
                    year = record.get("year") or ""
                    
                    subtitle_parts = []
                    if genre:
                        subtitle_parts.append(genre)
                    if year:
                        subtitle_parts.append(year)
                    if notable_mark:
                        subtitle_parts.append(notable_mark)
                    
                    results.append(SearchResult(
                        id=str(record["id"]),
                        label=record["name"],
                        type="song",
                        subtitle=" | ".join(subtitle_parts) if subtitle_parts else None
                    ))
                
                total += len(results)
        
        # 限制总结果数
        results = results[:limit]
        
        return SearchResponse(
            results=results,
            total=total,
            query=q
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"搜索失败: {str(e)}"
        )
