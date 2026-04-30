import { apiGet, apiPost } from "@/api/client";

export type ApiEnvelope<T> = { data: T; meta?: Record<string, unknown> };

export type GenreFlowNode = { id: string; name?: string | null };
export type GenreFlowLink = { source: string; target: string; value: number };
export type GenreFlowSeriesPoint = { year: number; value: number };
export type GenreFlowSeries = { genre: string; points: GenreFlowSeriesPoint[] };
export type GenreStat = { genre: string; song_count: number };

export type GenreFlowPayload = {
  nodes?: GenreFlowNode[] | null;
  links?: GenreFlowLink[] | null;
  series?: GenreFlowSeries[] | null;
};

export type GenreStatsPayload = {
  genres: GenreStat[];
  start_year: number;
  end_year: number;
};

export async function fetchGenreFlow(params: {
  start_year: number;
  end_year: number;
  metric: "style_edges" | "genre_mix";
  source_genre?: string;
  limit?: number;
}): Promise<GenreFlowPayload> {
  const res = await apiGet<ApiEnvelope<GenreFlowPayload>>("/analysis/genre-flow", {
    start_year: params.start_year,
    end_year: params.end_year,
    metric: params.metric,
    source_genre: params.source_genre,
    limit: params.limit ?? 100,
  });
  return res.data;
}

export async function fetchGenreStats(params: {
  start_year: number;
  end_year: number;
}): Promise<GenreStatsPayload> {
  const res = await apiGet<ApiEnvelope<GenreStatsPayload>>("/analysis/genre-stats", {
    start_year: params.start_year,
    end_year: params.end_year,
  });
  return res.data;
}

export type NormalizedProfile = {
  person_id: string;
  name: string;
  metrics: Record<string, number>;
  raw_metrics?: Record<string, number>;
};

export type PersonProfileNormalizedPayload = {
  profiles: NormalizedProfile[];
  dimensions: string[];
  anchor_id?: string;
  anchor_name?: string;
  normalization?: unknown;
};

export async function fetchPersonProfileNormalized(
  personIds: string[],
  startYear: number,
  endYear: number,
): Promise<PersonProfileNormalizedPayload> {
  const res = await apiGet<ApiEnvelope<PersonProfileNormalizedPayload>>("/analysis/person-profile", {
    person_ids: personIds.join(","),
    start_year: startYear,
    end_year: endYear,
    normalized: true,
  });
  return res.data;
}

export type SearchHit = {
  id: string;
  label: string;
  type: string;
  subtitle?: string | null;
};

export type SearchResponseBody = {
  results: SearchHit[];
  total: number;
  query: string;
};

export async function fetchSearch(
  q: string,
  type: "person" | "song" | "all" = "all",
  limit = 20,
): Promise<SearchResponseBody> {
  const res = await apiGet<ApiEnvelope<SearchResponseBody>>("/search", { q, type, limit });
  return res.data;
}

export type CareerYearAgg = {
  year: number;
  song_count: number;
  notable_count: number;
  genres: string[];
};

export type CareerSummary = {
  first_release_year: number | null;
  first_notable_year: number | null;
  fame_gap_years: number | null;
  peak_year: number | null;
  active_span_years: number;
  total_works: number;
};

export type CareerTrackPayload = {
  person: { id: string; name: string };
  summary: CareerSummary | null;
  by_year: CareerYearAgg[];
  works: unknown[];
};

export async function fetchCareerTrack(params: {
  person_id?: string;
  person_name?: string;
  start_year: number;
  end_year: number;
}): Promise<CareerTrackPayload> {
  const res = await apiGet<ApiEnvelope<CareerTrackPayload>>("/analysis/career-track", {
    person_id: params.person_id,
    person_name: params.person_name,
    start_year: params.start_year,
    end_year: params.end_year,
  });
  return res.data;
}

export type GalaxyGraphNode = {
  id: string;
  label: string;
  name?: string | null;
  props?: Record<string, unknown>;
};

export type GalaxyGraphLink = {
  source: string;
  target: string;
  type: string;
  props?: Record<string, unknown>;
};

export type InfluenceGalaxyPayload = {
  graph: { nodes: GalaxyGraphNode[]; links: GalaxyGraphLink[] };
  seed_people?: { id: string; name: string }[];
  clusters?: {
    component_id: number;
    node_count: number;
    edge_count: number;
    sample_nodes: { id: string; name: string }[];
  }[];
  bridge_nodes?: {
    node_id: string;
    name: string;
    label: string;
    bridge_score: number;
    degree: number;
  }[];
};

export async function fetchInfluenceSubgraph(params: {
  start_year: number;
  end_year: number;
  genres: string[];
  seed_person_ids: string[];
  rel_types?: string[];
  max_hops?: number;
  limit_nodes?: number;
  only_notable_songs?: boolean;
}): Promise<InfluenceGalaxyPayload> {
  const res = await apiPost<ApiEnvelope<InfluenceGalaxyPayload>>("/graph/subgraph", {
    start_year: params.start_year,
    end_year: params.end_year,
    genres: params.genres,
    seed_person_ids: params.seed_person_ids,
    rel_types: params.rel_types ?? [],
    max_hops: params.max_hops ?? 2,
    limit_nodes: params.limit_nodes ?? 500,
    only_notable_songs: params.only_notable_songs ?? false,
  });
  return res.data;
}

export async function fetchInfluenceExpand(params: {
  node_id: string;
  rel_types?: string[];
  direction?: "out" | "in" | "both";
  limit?: number;
  start_year?: number;
  end_year?: number;
  genres?: string[];
  only_notable_songs?: boolean;
}): Promise<InfluenceGalaxyPayload> {
  const res = await apiGet<ApiEnvelope<InfluenceGalaxyPayload>>(
    `/graph/expand/${encodeURIComponent(params.node_id)}`,
    {
      rel_types: params.rel_types?.join(","),
      direction: params.direction ?? "both",
      limit: params.limit ?? 180,
      start_year: params.start_year,
      end_year: params.end_year,
      genres: params.genres?.join(","),
      only_notable_songs: params.only_notable_songs ?? false,
    },
  );
  return res.data;
}
