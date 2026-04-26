from typing import Any, Optional

from pydantic import BaseModel, Field


class ApiMeta(BaseModel):
    truncated: bool = False
    node_count: Optional[int] = None
    link_count: Optional[int] = None
    total_hint: Optional[int] = None
    evidence_id: Optional[str] = None
    db: Optional[str] = None


class ApiResponse(BaseModel):
    data: Any
    meta: ApiMeta = Field(default_factory=ApiMeta)
