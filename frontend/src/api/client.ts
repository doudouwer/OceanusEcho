/** 路径前缀：默认 /api/v1，由 Vite 代理到后端 8000；若设 VITE_API_BASE_URL 须为绝对地址且含 /api/v1 */
const base = () =>
  (import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "") || "/api/v1";

/** path 为业务路径，如 `/analysis/genre-flow`（不含 /api/v1）；或完整 http(s) URL */
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
  // 浏览器中单参数 new URL("/api/...") 会抛 Invalid URL，必须用第二参数 base（当前页 origin → Vite 再代理到 8000）
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
