from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiMeta(BaseModel):
    truncated: bool = False
    node_count: int | None = None
    link_count: int | None = None
    total_hint: int | None = None
    evidence_id: str | None = None
    """可选：查询模板 + 参数 hash，供叙事 / Agent 追溯。"""
    db: str | None = None
    """connected | offline — 未配置密码或未连上 Neo4j 时为 offline。"""


class ApiResponse(BaseModel, Generic[T]):
    data: T
    meta: ApiMeta = Field(default_factory=ApiMeta)
