export type ApiEnvelope<T> = { data: T; meta?: Record<string, unknown> };

const apiBase = () => (import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || "/api/v1");

function resolveApiUrl(path: string): URL {
  const prefix = apiBase();
  const p = path.startsWith("/") ? path : `/${path}`;
  const joined = `${prefix}${p}`;
  if (joined.startsWith("http://") || joined.startsWith("https://")) return new URL(joined);
  return new URL(joined, window.location.origin);
}

async function parseJsonSafe(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

async function apiGet<T>(path: string, params?: Record<string, string | number | boolean | null | undefined>): Promise<T> {
  const url = resolveApiUrl(path);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") return;
      url.searchParams.set(key, String(value));
    });
  }
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  const body = await parseJsonSafe(res);
  if (!res.ok) throw new Error(`GET ${url.pathname} failed: ${res.status}`);
  return body as T;
}

async function apiPost<T>(path: string, json: unknown): Promise<T> {
  const url = resolveApiUrl(path);
  const res = await fetch(url, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(json),
  });
  const body = await parseJsonSafe(res);
  if (!res.ok) throw new Error(`POST ${url.pathname} failed: ${res.status}`);
  return body as T;
}

export type CareerYearAgg = {
  year: number;
  song_count: number;
  notable_count: number;
  genres: string[];
};

export type CareerTrackPayload = {
  person: { id: string; name: string };
  summary: {
    first_release_year: number | null;
    first_notable_year: number | null;
    fame_gap_years: number | null;
    peak_year: number | null;
    active_span_years: number;
    total_works: number;
  } | null;
  by_year: CareerYearAgg[];
  works: unknown[];
};

export type GenreFlowSeries = {
  genre: string;
  points: { year: number; value: number }[];
};

export type GenreFlowNode = { id: string; name?: string | null };
export type GenreFlowLink = { source: string; target: string; value: number };

export type GenreFlowPayload = {
  nodes?: GenreFlowNode[] | null;
  links?: GenreFlowLink[] | null;
  series?: GenreFlowSeries[] | null;
};

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
  bridge_nodes?: { node_id: string; name: string; label: string; bridge_score: number; degree: number }[];
};

export type NormalizedProfile = {
  person_id: string;
  name: string;
  metrics: Record<string, number>;
  raw_metrics?: Record<string, number>;
};

export type PersonProfilePayload = {
  profiles: NormalizedProfile[];
  dimensions: string[];
  anchor_id?: string;
  anchor_name?: string;
};

export type RisingStarCandidate = {
  person_id: string;
  name: string;
  score: number;
  reason: string;
  metrics: Record<string, number>;
};

export type RisingStarsPayload = {
  candidates: RisingStarCandidate[];
  genre: string | null;
  reference_person_id: string;
  start_year: number;
  end_year: number;
  recent_start_year: number;
};

export function fetchCareerTrack(personId: string, startYear: number, endYear: number) {
  return apiGet<ApiEnvelope<CareerTrackPayload>>("/analysis/career-track", {
    person_id: personId,
    start_year: startYear,
    end_year: endYear,
  }).then((res) => res.data);
}

export function fetchGenreFlow(
  startYear: number,
  endYear: number,
  options: { metric?: "genre_mix" | "style_edges"; sourceGenre?: string; limit?: number } = {},
) {
  return apiGet<ApiEnvelope<GenreFlowPayload>>("/analysis/genre-flow", {
    start_year: startYear,
    end_year: endYear,
    metric: options.metric ?? "genre_mix",
    source_genre: options.sourceGenre,
    limit: options.limit ?? 100,
  }).then((res) => res.data);
}

export function fetchInfluenceSubgraph(params: {
  startYear: number;
  endYear: number;
  genres: string[];
  seedPersonIds: string[];
  relTypes: string[];
  limitNodes?: number;
}) {
  return apiPost<ApiEnvelope<InfluenceGalaxyPayload>>("/graph/subgraph", {
    start_year: params.startYear,
    end_year: params.endYear,
    genres: params.genres,
    seed_person_ids: params.seedPersonIds,
    rel_types: params.relTypes,
    max_hops: 2,
    limit_nodes: params.limitNodes ?? 180,
    only_notable_songs: false,
  }).then((res) => res.data);
}

export function fetchPersonProfile(personIds: string[], startYear: number, endYear: number) {
  return apiGet<ApiEnvelope<PersonProfilePayload>>("/analysis/person-profile", {
    person_ids: personIds.join(","),
    start_year: startYear,
    end_year: endYear,
    normalized: true,
  }).then((res) => res.data);
}

export function fetchRisingStars(startYear: number, endYear: number, limit = 3) {
  return apiGet<ApiEnvelope<RisingStarsPayload>>("/analysis/rising-stars", {
    start_year: startYear,
    end_year: endYear,
    genre: "Oceanus Folk",
    reference_person_id: "17255",
    limit,
  }).then((res) => res.data);
}
