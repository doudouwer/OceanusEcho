from typing import Optional

from pydantic import BaseModel


class SearchHit(BaseModel):
    id: str
    label: str
    subtitle: Optional[str] = None


class SearchData(BaseModel):
    hits: list[SearchHit]
