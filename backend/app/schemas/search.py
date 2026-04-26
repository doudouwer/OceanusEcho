from typing import Optional

from pydantic import BaseModel


class SearchHit(BaseModel):
    id: str
    label: str
    type: str = "person"
    subtitle: Optional[str] = None


class SearchResponseData(BaseModel):
    results: list[SearchHit]
    total: int = 0
    query: str = ""
