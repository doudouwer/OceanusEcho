from typing import Optional

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


class GenreSankeyNode(BaseModel):
    id: str


class GenreSankeyLink(BaseModel):
    source: str
    target: str
    value: float


class GenreStreamPoint(BaseModel):
    year: int
    value: float


class GenreSeries(BaseModel):
    genre: str
    points: list[GenreStreamPoint]


class GenreFlowData(BaseModel):
    """view=sankey 时填充 nodes/links；view=stream 时填充 series。"""

    nodes: Optional[list[GenreSankeyNode]] = None
    links: Optional[list[GenreSankeyLink]] = None
    series: Optional[list[GenreSeries]] = None


class PersonProfileMetrics(BaseModel):
    song_count: int = 0
    notable_rate: float = 0.0
    active_years: int = 0
    unique_collaborators: int = 0
    genre_entropy: float = 0.0
    degree: int = 0
    pagerank: float = 0.0


class PersonProfileRow(BaseModel):
    person_id: str
    name: str
    metrics: PersonProfileMetrics


class PersonProfileData(BaseModel):
    profiles: list[PersonProfileRow]
    dimensions: list[str]


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
