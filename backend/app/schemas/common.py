from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiMeta(BaseModel):
    truncated: bool = False
    node_count: Optional[int] = None
    link_count: Optional[int] = None
    total_hint: Optional[int] = None
    evidence_id: Optional[str] = None
    """可选：查询模板 + 参数 hash，供叙事 / Agent 追溯。"""
    db: Optional[str] = None
    """connected | offline — 未配置密码或未连上 Neo4j 时为 offline。"""


class ApiResponse(BaseModel, Generic[T]):
    data: T
    meta: ApiMeta = Field(default_factory=ApiMeta)
