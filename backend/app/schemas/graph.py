from pydantic import BaseModel, Field, model_validator


class GraphNode(BaseModel):
    id: str
    label: str
    name: str | None = None
    props: dict = Field(default_factory=dict)


class GraphLink(BaseModel):
    source: str
    target: str
    type: str
    props: dict = Field(default_factory=dict)


class GraphPayload(BaseModel):
    nodes: list[GraphNode]
    links: list[GraphLink]


class SubgraphRequest(BaseModel):
    start_year: int = Field(ge=1900, le=2200)
    end_year: int = Field(ge=1900, le=2200)
    genres: list[str] = Field(default_factory=list)
    seed_person_ids: list[str] = Field(default_factory=list)
    rel_types: list[str] = Field(default_factory=list)
    limit_nodes: int = Field(default=800, ge=1, le=20_000)
    only_notable_songs: bool = False

    @model_validator(mode="after")
    def year_order(self) -> "SubgraphRequest":
        if self.end_year < self.start_year:
            raise ValueError("end_year must be >= start_year")
        return self


class ExpandParams(BaseModel):
    rel_types: str | None = None
    direction: str = "both"
    limit: int = Field(default=200, ge=1, le=5000)
