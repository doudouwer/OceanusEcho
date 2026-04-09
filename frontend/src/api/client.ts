const base = () =>
  (import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "") || "/api/v1";

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

export async function apiGet<T>(path: string, params?: Record<string, string | number | null | undefined>): Promise<T> {
  const url = new URL(path.startsWith("http") ? path : `${base()}${path.startsWith("/") ? path : `/${path}`}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
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
  const url = `${base()}${path.startsWith("/") ? path : `/${path}`}`;
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
