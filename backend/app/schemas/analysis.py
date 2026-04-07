from pydantic import BaseModel, Field


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


class CareerTrackData(BaseModel):
    person: PersonRef
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

    nodes: list[GenreSankeyNode] | None = None
    links: list[GenreSankeyLink] | None = None
    series: list[GenreSeries] | None = None


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
