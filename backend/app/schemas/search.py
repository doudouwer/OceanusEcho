from pydantic import BaseModel


class SearchHit(BaseModel):
    id: str
    label: str
    subtitle: str | None = None


class SearchData(BaseModel):
    hits: list[SearchHit]
