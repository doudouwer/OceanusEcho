from pydantic import BaseModel, Field

from app.schemas.graph import GraphPayload


class PersonRef(BaseModel):
    id: str
    name: str


class YearAgg(BaseModel):
    year: int
    song_count: int
    notable_count: int
    genres: list[str] = Field(default_factory=list)


class WorkItem(BaseModel):
    song_id: str
    title: str
    release_date: str
    notable: bool
    genre: str | None = None


class CareerSummary(BaseModel):
    first_release_year: int | None = None
    first_notable_year: int | None = None
    fame_gap_years: int | None = None
    peak_year: int | None = None
    active_span_years: int = 0
    total_works: int = 0


class CareerTrackData(BaseModel):
    person: PersonRef
    summary: CareerSummary | None = None
    by_year: list[YearAgg]
    works: list[WorkItem]


class GalaxyBridgeNode(BaseModel):
    node_id: str
    name: str
    label: str
    bridge_score: float
    degree: int


class GalaxyCluster(BaseModel):
    component_id: int
    node_count: int
    edge_count: int
    sample_nodes: list[PersonRef] = Field(default_factory=list)


class InfluenceGalaxyData(BaseModel):
    graph: GraphPayload
    seed_people: list[PersonRef] = Field(default_factory=list)
    clusters: list[GalaxyCluster] = Field(default_factory=list)
    bridge_nodes: list[GalaxyBridgeNode] = Field(default_factory=list)
