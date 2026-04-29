"""
在线接口验证 + Influence Galaxy 效果预览脚本。

用法:
    python -m scripts.test_services
    python -m scripts.test_services --base-url http://127.0.0.1:8000 --seed-person-id 17255
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener


DEFAULT_REL_TYPES = [
    "IN_STYLE_OF",
    "INTERPOLATES_FROM",
    "PERFORMER_OF",
    "COMPOSER_OF",
    "LYRICIST_OF",
    "PRODUCER_OF",
    "MEMBER_OF",
]

_DIRECT_HTTP = build_opener(ProxyHandler({}))


def _build_url(base_url: str, path: str, params: dict[str, Any] | None = None) -> str:
    base = base_url.rstrip("/")
    p = path if path.startswith("/") else f"/{path}"
    if not params:
        return f"{base}{p}"
    qs = urlencode({k: v for k, v in params.items() if v is not None})
    return f"{base}{p}?{qs}" if qs else f"{base}{p}"


def _request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: float = 15.0,
) -> Any:
    url = _build_url(base_url, path, params)
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url=url, data=data, headers=headers, method=method)
    try:
        with _DIRECT_HTTP.open(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            raw = resp.read().decode(charset, errors="replace")
            return json.loads(raw) if raw else None
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: HTTP {e.code} {body}") from e
    except URLError as e:
        reason = str(e.reason)
        hint = ""
        if "Connection refused" in reason or "111" in reason:
            hint = " (API 可能未启动，请先运行: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000)"
        raise RuntimeError(f"{method} {url} failed: {reason}{hint}") from e


def _ensure(cond: bool, msg: str) -> None:
    if not cond:
        raise RuntimeError(msg)


def _unwrap_data(envelope: dict[str, Any], name: str) -> dict[str, Any]:
    _ensure(isinstance(envelope, dict), f"{name}: response is not a JSON object")
    _ensure("data" in envelope, f"{name}: response missing `data` field")
    data = envelope["data"]
    _ensure(isinstance(data, dict), f"{name}: `data` must be an object")
    return data


def _summarize_graph_payload(data: dict[str, Any]) -> dict[str, Any]:
    graph = data.get("graph") or {}
    nodes = graph.get("nodes") or []
    links = graph.get("links") or []
    label_counter = Counter()
    rel_counter = Counter()
    for n in nodes:
        if isinstance(n, dict):
            label_counter[str(n.get("label") or "Node")] += 1
    for l in links:
        if isinstance(l, dict):
            rel_counter[str(l.get("type") or "REL")] += 1

    clusters = data.get("clusters") or []
    bridges = data.get("bridge_nodes") or []
    return {
        "node_count": len(nodes),
        "link_count": len(links),
        "label_top": label_counter.most_common(6),
        "relation_top": rel_counter.most_common(8),
        "cluster_count": len(clusters),
        "bridge_count": len(bridges),
        "top_bridges": bridges[:5],
    }


def _pick_expand_node(data: dict[str, Any], seed_person_id: str) -> str | None:
    bridges = data.get("bridge_nodes") or []
    for b in bridges:
        if isinstance(b, dict) and b.get("node_id"):
            return str(b["node_id"])

    graph = data.get("graph") or {}
    nodes = graph.get("nodes") or []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        if str(n.get("id")) == seed_person_id:
            return seed_person_id
    for n in nodes:
        if not isinstance(n, dict):
            continue
        if str(n.get("label")) in {"Person", "MusicalGroup"} and n.get("id") is not None:
            return str(n["id"])
    return None


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _pretty_print_summary(title: str, summary: dict[str, Any]) -> None:
    print(f"\n[{title}]")
    print(f"  nodes={summary['node_count']}  links={summary['link_count']}")
    print(f"  labels={summary['label_top']}")
    print(f"  relations={summary['relation_top']}")
    print(
        f"  communities={summary['cluster_count']}  bridge_nodes={summary['bridge_count']}"
    )
    if summary["top_bridges"]:
        top = []
        for b in summary["top_bridges"]:
            if not isinstance(b, dict):
                continue
            name = b.get("name") or b.get("node_id")
            score = b.get("bridge_score")
            top.append(f"{name}({score})")
        print(f"  top_bridge_preview={', '.join(top)}")


def run(args: argparse.Namespace) -> int:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.output_dir).expanduser().resolve() / f"run_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("==========================================")
    print("OceanusEcho 在线验证 + Galaxy 预览")
    print("==========================================")
    print(f"base_url={args.base_url}")
    print(f"output={out_dir}")
    print("network=direct (proxy disabled)")

    health = _request_json(args.base_url, "/health", timeout=args.timeout)
    _write_json(out_dir / "health.json", health)
    _ensure(isinstance(health, dict), "/health must return JSON object")
    _ensure(
        health.get("neo4j_async") == "connected",
        "Neo4j async driver is not connected. 请先启动 Neo4j 并导入 MC1 数据。",
    )
    print(f"health={health.get('status')} neo4j_async={health.get('neo4j_async')}")

    search_env = _request_json(
        args.base_url,
        "/api/v1/search",
        params={"q": "Sailor", "type": "person", "limit": 10},
        timeout=args.timeout,
    )
    _write_json(out_dir / "search_sailor.json", search_env)
    search_data = _unwrap_data(search_env, "search")
    _ensure(isinstance(search_data.get("results"), list), "search: `results` should be a list")
    print(f"search_results={len(search_data['results'])}")

    career_env = _request_json(
        args.base_url,
        "/api/v1/analysis/career-track",
        params={
            "person_id": args.seed_person_id,
            "start_year": args.start_year,
            "end_year": args.end_year,
        },
        timeout=args.timeout,
    )
    _write_json(out_dir / "career_track.json", career_env)
    career_data = _unwrap_data(career_env, "career-track")
    print(
        "career="
        f"{career_data.get('person', {}).get('name', args.seed_person_id)} "
        f"works={len(career_data.get('works') or [])}"
    )

    subgraph_payload = {
        "start_year": args.start_year,
        "end_year": args.end_year,
        "genres": args.genres,
        "seed_person_ids": [args.seed_person_id],
        "rel_types": DEFAULT_REL_TYPES,
        "max_hops": args.max_hops,
        "limit_nodes": args.limit_nodes,
        "only_notable_songs": args.only_notable_songs,
    }
    subgraph_env = _request_json(
        args.base_url,
        "/api/v1/graph/subgraph",
        method="POST",
        payload=subgraph_payload,
        timeout=args.timeout,
    )
    _write_json(out_dir / "galaxy_subgraph.json", subgraph_env)
    subgraph_data = _unwrap_data(subgraph_env, "graph/subgraph")
    summary = _summarize_graph_payload(subgraph_data)
    _ensure(summary["node_count"] > 0, "subgraph returned 0 nodes")
    _ensure(summary["link_count"] > 0, "subgraph returned 0 links")
    _pretty_print_summary("Galaxy Subgraph", summary)

    expand_node = _pick_expand_node(subgraph_data, args.seed_person_id)
    _ensure(expand_node is not None, "cannot find a node for expand test")
    expand_env = _request_json(
        args.base_url,
        f"/api/v1/graph/expand/{expand_node}",
        params={
            "rel_types": ",".join(DEFAULT_REL_TYPES),
            "direction": "both",
            "limit": args.expand_limit,
            "start_year": args.start_year,
            "end_year": args.end_year,
            "genres": ",".join(args.genres),
            "only_notable_songs": str(args.only_notable_songs).lower(),
        },
        timeout=args.timeout,
    )
    _write_json(out_dir / "galaxy_expand.json", expand_env)
    expand_data = _unwrap_data(expand_env, "graph/expand")
    expand_summary = _summarize_graph_payload(expand_data)
    _ensure(expand_summary["node_count"] > 0, "expand returned 0 nodes")
    _pretty_print_summary("Galaxy Expand", expand_summary)
    print(f"expand_node={expand_node}")

    genre_env = _request_json(
        args.base_url,
        "/api/v1/analysis/genre-flow",
        params={
            "start_year": args.start_year,
            "end_year": args.end_year,
            "metric": "style_edges",
            "source_genre": args.genres[0] if len(args.genres) == 1 else None,
            "limit": 50,
        },
        timeout=args.timeout,
    )
    _write_json(out_dir / "genre_flow_style_edges.json", genre_env)
    genre_data = _unwrap_data(genre_env, "genre-flow")
    print(
        f"genre_flow nodes={len(genre_data.get('nodes') or [])} "
        f"links={len(genre_data.get('links') or [])}"
    )

    profile_env = _request_json(
        args.base_url,
        "/api/v1/analysis/person-profile",
        params={
            "person_ids": args.seed_person_id,
            "start_year": args.start_year,
            "end_year": args.end_year,
            "normalized": "true",
        },
        timeout=args.timeout,
    )
    _write_json(out_dir / "person_profile.json", profile_env)
    profile_data = _unwrap_data(profile_env, "person-profile")
    print(f"profile_count={len(profile_data.get('profiles') or [])}")

    report = {
        "base_url": args.base_url,
        "time_window": [args.start_year, args.end_year],
        "genres": args.genres,
        "seed_person_id": args.seed_person_id,
        "subgraph_summary": summary,
        "expand_summary": expand_summary,
        "output_dir": str(out_dir),
    }
    _write_json(out_dir / "summary.json", report)

    print("\n✅ 全部检查通过。")
    print(f"预览数据已写入: {out_dir}")
    print("可重点查看: galaxy_subgraph.json / galaxy_expand.json / summary.json")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OceanusEcho 在线验证 + Galaxy 预览脚本")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--start-year", type=int, default=2023)
    parser.add_argument("--end-year", type=int, default=2040)
    parser.add_argument("--genres", default="Oceanus Folk", help="逗号分隔，例如 Oceanus Folk,Indie Pop")
    parser.add_argument("--seed-person-id", default="17255")
    parser.add_argument("--max-hops", type=int, default=2)
    parser.add_argument("--limit-nodes", type=int, default=500)
    parser.add_argument("--expand-limit", type=int, default=180)
    parser.add_argument("--only-notable-songs", action="store_true")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--output-dir", default="/tmp/oceanusecho-preview")
    args = parser.parse_args(argv)
    args.genres = [x.strip() for x in str(args.genres).split(",") if x.strip()]
    if args.end_year < args.start_year:
        parser.error("--end-year must be >= --start-year")
    if not args.genres:
        parser.error("--genres cannot be empty")
    return args


def main() -> int:
    args = parse_args(sys.argv[1:])
    try:
        return run(args)
    except Exception as e:
        print(f"\n❌ 失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
