/** Path prefix: defaults to /api/v1 via Vite proxy to backend :8000; VITE_API_BASE_URL must be absolute and include /api/v1 */
const base = () =>
  (import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "") || "/api/v1";

/** `path` is a business path like `/analysis/genre-flow` (without /api/v1), or a full http(s) URL */
function resolveApiUrl(path: string): URL {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return new URL(path);
  }
  const p = path.startsWith("/") ? path : `/${path}`;
  const prefix = base();
  const joined = `${prefix.replace(/\/$/, "")}${p}`;
  if (joined.startsWith("http://") || joined.startsWith("https://")) {
    return new URL(joined);
  }
  // In the browser, new URL("/api/...") with one arg throws Invalid URL; use base (page origin → Vite proxies to :8000)
  const origin =
    typeof window !== "undefined" && window.location?.origin
      ? window.location.origin
      : "http://127.0.0.1:5173";
  return new URL(joined, origin);
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
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

export async function apiGet<T>(
  path: string,
  params?: Record<string, string | number | boolean | null | undefined>,
): Promise<T> {
  const pathPart = path.startsWith("http") ? path : path.startsWith("/") ? path : `/${path}`;
  const url = resolveApiUrl(pathPart);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v === undefined || v === null || v === "") return;
      url.searchParams.set(k, String(v));
    });
  }
  const res = await fetch(url.toString(), {
    headers: { Accept: "application/json" },
  });
  const body = await parseJsonSafe(res);
  if (!res.ok) {
    throw new ApiError(`GET ${url.pathname} failed`, res.status, body);
  }
  return body as T;
}

export async function apiPost<T>(path: string, json: unknown): Promise<T> {
  const pathPart = path.startsWith("http") ? path : path.startsWith("/") ? path : `/${path}`;
  const url = resolveApiUrl(pathPart).toString();
  const res = await fetch(url, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(json),
  });
  const body = await parseJsonSafe(res);
  if (!res.ok) {
    throw new ApiError(`POST ${path} failed`, res.status, body);
  }
  return body as T;
}
