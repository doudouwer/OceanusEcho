from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ========== 通用响应模型 ==========

class MetaInfo(BaseModel):
    """响应元信息"""
    truncated: bool = False
    node_count: Optional[int] = None
    link_count: Optional[int] = None
    total_hint: Optional[int] = None
    evidence_id: Optional[str] = None


class APIResponse(BaseModel):
    """统一 API 响应格式"""
    data: Any
    meta: MetaInfo = Field(default_factory=MetaInfo)


# ========== 流派演变 (Genre Flow) 相关模型 ==========

class GenreFlowLink(BaseModel):
    """桑基图的边"""
    source: str
    target: str
    value: int


class GenreFlowNode(BaseModel):
    """桑基图的节点"""
    id: str
    name: Optional[str] = None


class GenreFlowSeriesPoint(BaseModel):
    """河流图数据点"""
    year: int
    value: float


class GenreFlowSeries(BaseModel):
    """河流图数据系列"""
    genre: str
    points: List[GenreFlowSeriesPoint]


class GenreFlowData(BaseModel):
    """流派演变数据"""
    nodes: Optional[List[GenreFlowNode]] = None
    links: Optional[List[GenreFlowLink]] = None
    series: Optional[List[GenreFlowSeries]] = None


class GenreFlowRequest(BaseModel):
    """流派演变请求参数"""
    start_year: int = Field(..., ge=1970, le=2050, description="起始年份")
    end_year: int = Field(..., ge=1970, le=2050, description="结束年份")
    metric: str = Field(default="style_edges", description="指标类型: style_edges | song_cowrite | genre_mix")
    source_genre: Optional[str] = Field(None, description="源流派，用于聚焦")
    limit: int = Field(default=100, ge=1, le=500, description="返回结果上限")


# ========== 艺人画像 (Star Profiler) 相关模型 ==========

class PersonMetrics(BaseModel):
    """艺人指标"""
    song_count: int = 0
    notable_count: int = 0
    notable_rate: float = 0.0
    active_years: int = 0
    unique_collaborators: int = 0
    genre_entropy: float = 0.0
    degree: int = 0
    pagerank: float = 0.0
    song_cowrite_count: int = 0
    style_influence_count: int = 0


class PersonProfile(BaseModel):
    """单人画像"""
    person_id: str
    name: str
    metrics: PersonMetrics
    top_genres: Optional[List[str]] = None
    top_collaborators: Optional[List[Dict[str, Any]]] = None


class PersonProfileData(BaseModel):
    """艺人画像数据"""
    profiles: List[PersonProfile]
    dimensions: List[str] = [
        "song_count", "notable_rate", "active_years", 
        "unique_collaborators", "genre_entropy", "degree", "pagerank"
    ]


class PersonProfileRequest(BaseModel):
    """艺人画像请求参数"""
    person_ids: List[str] = Field(..., min_length=1, max_length=20, description="艺人 ID 列表")
    start_year: Optional[int] = Field(None, ge=1970, le=2050, description="起始年份（可选）")
    end_year: Optional[int] = Field(None, ge=1970, le=2050, description="结束年份（可选）")


# ========== 搜索相关模型 ==========

class SearchResult(BaseModel):
    """搜索结果项"""
    id: str
    label: str
    type: str
    subtitle: Optional[str] = None
    props: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """搜索响应"""
    results: List[SearchResult]
    total: int
    query: str


class SearchRequest(BaseModel):
    """搜索请求参数"""
    q: str = Field(..., min_length=1, max_length=100, description="搜索关键词")
    type: str = Field(default="all", description="搜索类型: person | song | all")
    limit: int = Field(default=20, ge=1, le=100, description="返回结果上限")
