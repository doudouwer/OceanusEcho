from __future__ import annotations

import json
import math
from collections import defaultdict, deque
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.constants import DEFAULT_REL_TYPES
from app.schemas.graph import GraphLink, GraphNode
from app.services.neo4j_serialize import node_public_id


GRAPH_PATH = Path(__file__).resolve().parents[3] / "MC1_release" / "MC1_graph.json"


def _safe_year(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text[:4])
    except ValueError:
        return None


def _norm(text: str) -> str:
    return text.strip().lower()


def _edge_type(edge: dict[str, Any]) -> str:
    return str(edge.get("Edge Type") or "")


def _node_type(node: dict[str, Any]) -> str:
    return str(node.get("Node Type") or "Node")


def _node_name(node: dict[str, Any]) -> str:
    return str(node.get("name") or "")


def _node_to_public(node: dict[str, Any]) -> GraphNode:
    props = dict(node)
    pid = str(props.get("id"))
    label = _node_type(node)
    name = props.get("name")
    extra = {k: v for k, v in props.items() if k not in {"id", "name"}}
    return GraphNode(id=pid, label=label, name=str(name) if name is not None else None, props=extra)


def _link_to_public(source_id: str, target_id: str, edge: dict[str, Any]) -> GraphLink:
    return GraphLink(
        source=source_id,
        target=target_id,
        type=_edge_type(edge),
        props={k: v for k, v in edge.items() if k not in {"source", "target", "key", "Edge Type"}},
    )


@dataclass(slots=True)
class LocalGraph:
    nodes: list[dict[str, Any]]
    links: list[dict[str, Any]]
    node_by_id: dict[str, dict[str, Any]]
    node_ids_by_name: dict[str, list[str]]
    out_edges: dict[str, list[int]]
    in_edges: dict[str, list[int]]

    def find_nodes(self, query: str, type_: str | None = None) -> list[dict[str, Any]]:
        q = _norm(query)
        if not q:
            return []
        hits: list[dict[str, Any]] = []
        for node in self.nodes:
            if type_ is not None and _node_type(node).lower() != type_.lower():
                continue
            name = _node_name(node)
            stage = str(node.get("stage_name") or "")
            if q in _norm(name) or q in _norm(stage):
                hits.append(node)
        return hits

    def resolve_node(self, node_id_or_name: str) -> dict[str, Any] | None:
        if node_id_or_name is None:
            return None
        key = str(node_id_or_name).strip()
        if not key:
            return None
        if key in self.node_by_id:
            return self.node_by_id[key]
        matches = self.find_nodes(key)
        return matches[0] if matches else None

    def resolve_person(self, person_id: str | None, person_name: str | None) -> dict[str, Any] | None:
        if person_id:
            node = self.resolve_node(person_id)
            if node is not None and _node_type(node) == "Person":
                return node
        if person_name:
            matches = [n for n in self.find_nodes(person_name, "Person")]
            if matches:
                return matches[0]
        return None

    def _passes_work_filters(
        self,
        node: dict[str, Any],
        start_year: int,
        end_year: int,
        genres: set[str],
        only_notable_songs: bool,
    ) -> bool:
        kind = _node_type(node)
        if kind not in {"Song", "Album"}:
            return True
        year = _safe_year(node.get("release_date"))
        if year is not None and not (start_year <= year <= end_year):
            return False
        if genres and str(node.get("genre") or "") not in genres:
            return False
        if only_notable_songs and not bool(node.get("notable")):
            return False
        return True

    def _edge_allowed(
        self,
        edge: dict[str, Any],
        start_year: int,
        end_year: int,
        genres: set[str],
        only_notable_songs: bool,
    ) -> bool:
        source = self.node_by_id.get(str(edge.get("source")))
        target = self.node_by_id.get(str(edge.get("target")))
        if source is None or target is None:
            return False
        return self._passes_work_filters(source, start_year, end_year, genres, only_notable_songs) and self._passes_work_filters(
            target, start_year, end_year, genres, only_notable_songs
        )

    def _allowed_edge_indices(
        self,
        rel_types: set[str],
        start_year: int,
        end_year: int,
        genres: set[str],
        only_notable_songs: bool,
    ) -> list[int]:
        allowed: list[int] = []
        for idx, edge in enumerate(self.links):
            if rel_types and _edge_type(edge) not in rel_types:
                continue
            if not self._edge_allowed(edge, start_year, end_year, genres, only_notable_songs):
                continue
            allowed.append(idx)
        return allowed

    def _edge_map(self, edge_indices: list[int]) -> tuple[dict[str, list[int]], dict[str, list[int]]]:
        out_map: dict[str, list[int]] = defaultdict(list)
        in_map: dict[str, list[int]] = defaultdict(list)
        for idx in edge_indices:
            edge = self.links[idx]
            sid = str(edge.get("source"))
            tid = str(edge.get("target"))
            out_map[sid].append(idx)
            in_map[tid].append(idx)
        return out_map, in_map

    def _default_seed_nodes(
        self,
        edge_indices: list[int],
        max_seeds: int = 8,
    ) -> list[str]:
        scores: dict[str, int] = defaultdict(int)
        for idx in edge_indices:
            edge = self.links[idx]
            sid = str(edge.get("source"))
            tid = str(edge.get("target"))
            if _node_type(self.node_by_id[sid]) == "Person":
                scores[sid] += 1
            if _node_type(self.node_by_id[tid]) == "Person":
                scores[tid] += 1
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        return [node_id for node_id, _ in ranked[:max_seeds]]

    def _expand_bfs(
        self,
        seed_ids: list[str],
        edge_indices: list[int],
        limit_nodes: int,
    ) -> tuple[list[str], list[int], dict[str, int]]:
        out_map, in_map = self._edge_map(edge_indices)
        allowed_edges = set(edge_indices)
        visited_nodes: dict[str, int] = {}
        queue: deque[tuple[str, int]] = deque()
        for sid in seed_ids:
            if sid in self.node_by_id:
                visited_nodes[sid] = 0
                queue.append((sid, 0))

        selected_edges: list[int] = []
        seen_edges: set[int] = set()
        while queue and len(visited_nodes) < limit_nodes:
            node_id, dist = queue.popleft()
            incident = out_map.get(node_id, []) + in_map.get(node_id, [])
            incident.sort(key=lambda idx: (_edge_type(self.links[idx]), idx))
            for edge_idx in incident:
                if edge_idx not in allowed_edges or edge_idx in seen_edges:
                    continue
                seen_edges.add(edge_idx)
                selected_edges.append(edge_idx)
                edge = self.links[edge_idx]
                for neighbor in (str(edge.get("source")), str(edge.get("target"))):
                    if neighbor not in self.node_by_id or neighbor in visited_nodes:
                        continue
                    if len(visited_nodes) >= limit_nodes:
                        break
                    visited_nodes[neighbor] = dist + 1
                    queue.append((neighbor, dist + 1))
        return list(visited_nodes.keys()), selected_edges, visited_nodes

    def subgraph(
        self,
        start_year: int,
        end_year: int,
        genres: list[str],
        seed_person_ids: list[str],
        rel_types: list[str],
        limit_nodes: int,
        only_notable_songs: bool,
    ) -> tuple[list[GraphNode], list[GraphLink], dict[str, Any]]:
        rel_set = {DEFAULT_REL_TYPES.get(r.strip().upper(), r.strip()) for r in rel_types if r.strip()}
        if not rel_set:
            rel_set = {DEFAULT_REL_TYPES["PERFORMER_OF"], DEFAULT_REL_TYPES["IN_STYLE_OF"]}
        genre_set = {g for g in genres if g}
        edge_indices = self._allowed_edge_indices(rel_set, start_year, end_year, genre_set, only_notable_songs)
        if not edge_indices:
            return [], [], {"truncated": False, "node_count": 0, "link_count": 0, "seed_count": 0}

        seed_ids: list[str] = []
        for pid in seed_person_ids:
            node = self.resolve_node(pid)
            if node is not None:
                seed_ids.append(str(node.get("id")))
        if not seed_ids:
            seed_ids = self._default_seed_nodes(edge_indices)

        node_ids, selected_edges, visited_depth = self._expand_bfs(seed_ids, edge_indices, limit_nodes)
        if not node_ids:
            return [], [], {"truncated": False, "node_count": 0, "link_count": 0, "seed_count": len(seed_ids)}

        # Keep the graph readable by preferring shallower nodes when trimming.
        ranked_nodes = sorted(node_ids, key=lambda nid: (visited_depth.get(nid, 99), _node_type(self.node_by_id[nid]), _node_name(self.node_by_id[nid]), nid))
        trimmed_ids = ranked_nodes[:limit_nodes]
        trimmed = set(trimmed_ids)

        nodes: list[GraphNode] = []
        node_seen: set[str] = set()
        for nid in trimmed_ids:
            node = self.node_by_id[nid]
            if nid in node_seen:
                continue
            nodes.append(_node_to_public(node))
            node_seen.add(nid)

        links: list[GraphLink] = []
        for edge_idx in selected_edges:
            edge = self.links[edge_idx]
            sid = str(edge.get("source"))
            tid = str(edge.get("target"))
            if sid not in trimmed or tid not in trimmed:
                continue
            links.append(_link_to_public(sid, tid, edge))

        return nodes, links, {
            "truncated": len(node_ids) > limit_nodes or len(selected_edges) > len(links),
            "node_count": len(nodes),
            "link_count": len(links),
            "seed_count": len(seed_ids),
        }

    def expand(
        self,
        node_id: str,
        rel_types: list[str] | None,
        direction: str,
        limit: int,
    ) -> tuple[list[GraphNode], list[GraphLink], dict[str, Any]]:
        node = self.resolve_node(node_id)
        if node is None:
            return [], [], {"truncated": False, "node_count": 0, "link_count": 0}

        rel_set = {DEFAULT_REL_TYPES.get(r.strip().upper(), r.strip()) for r in (rel_types or []) if r.strip()}
        if not rel_set:
            rel_set = {DEFAULT_REL_TYPES["PERFORMER_OF"], DEFAULT_REL_TYPES["IN_STYLE_OF"]}

        node_id_str = str(node.get("id"))
        incident: list[int] = []
        for idx, edge in enumerate(self.links):
            if _edge_type(edge) not in rel_set:
                continue
            sid = str(edge.get("source"))
            tid = str(edge.get("target"))
            if direction == "out" and sid != node_id_str:
                continue
            if direction == "in" and tid != node_id_str:
                continue
            if direction == "both" and node_id_str not in {sid, tid}:
                continue
            if not self._edge_allowed(edge, 1900, 2200, set(), False):
                continue
            incident.append(idx)

        incident = incident[:limit]
        node_ids: set[str] = {node_id_str}
        links: list[GraphLink] = []
        for edge_idx in incident:
            edge = self.links[edge_idx]
            sid = str(edge.get("source"))
            tid = str(edge.get("target"))
            node_ids.add(sid)
            node_ids.add(tid)
            links.append(_link_to_public(sid, tid, edge))

        nodes = [_node_to_public(self.node_by_id[nid]) for nid in sorted(node_ids, key=lambda x: (_node_type(self.node_by_id[x]), _node_name(self.node_by_id[x]), x))]
        return nodes, links, {
            "truncated": len(incident) >= limit,
            "node_count": len(nodes),
            "link_count": len(links),
        }

    def career_track(
        self,
        person_id: str | None,
        person_name: str | None,
        start_year: int,
        end_year: int,
    ) -> dict[str, Any] | None:
        person = self.resolve_person(person_id, person_name)
        if person is None:
            return None

        pid = str(person.get("id"))
        works: list[dict[str, Any]] = []
        by_year: dict[int, dict[str, Any]] = defaultdict(lambda: {"song_count": 0, "notable_count": 0, "genres": set()})

        for edge in self.links:
            if _edge_type(edge) != "PerformerOf" or str(edge.get("source")) != pid:
                continue
            target = self.node_by_id.get(str(edge.get("target")))
            if target is None or _node_type(target) != "Song":
                continue
            year = _safe_year(target.get("release_date"))
            if year is None or not (start_year <= year <= end_year):
                continue
            genre = target.get("genre")
            notable = bool(target.get("notable"))
            by_year[year]["song_count"] += 1
            by_year[year]["notable_count"] += int(notable)
            if genre:
                by_year[year]["genres"].add(str(genre))
            works.append(
                {
                    "song_id": str(target.get("id")),
                    "title": str(target.get("name") or ""),
                    "release_date": str(target.get("release_date") or ""),
                    "notable": notable,
                    "genre": str(genre) if genre is not None else None,
                }
            )

        if not works:
            return None

        years = sorted(by_year)
        first_year = min(years)
        last_year = max(years)
        notable_years = [year for year, item in by_year.items() if item["notable_count"] > 0]
        summary = {
            "first_release_year": first_year,
            "first_notable_year": min(notable_years) if notable_years else None,
            "fame_gap_years": (min(notable_years) - first_year) if notable_years else None,
            "peak_year": max(by_year.items(), key=lambda item: (item[1]["song_count"], item[0]))[0],
            "active_span_years": last_year - first_year + 1,
            "total_works": len(works),
        }

        career_rows = [
            {
                "year": year,
                "song_count": payload["song_count"],
                "notable_count": payload["notable_count"],
                "genres": sorted(payload["genres"]),
            }
            for year, payload in sorted(by_year.items())
        ]

        return {
            "person": {"id": pid, "name": str(person.get("name") or "")},
            "summary": summary,
            "by_year": career_rows,
            "works": sorted(works, key=lambda item: (item["release_date"], item["title"])),
        }

    def person_profile(self, person_id: str, start_year: int, end_year: int) -> dict[str, Any] | None:
        person = self.resolve_node(person_id)
        if person is None or _node_type(person) != "Person":
            return None

        pid = str(person.get("id"))
        song_ids: list[str] = []
        songs: list[dict[str, Any]] = []
        collaborators: set[str] = set()
        genre_counts: dict[str, int] = defaultdict(int)
        notable_n = 0
        years: set[int] = set()

        for edge in self.links:
            if _edge_type(edge) != "PerformerOf" or str(edge.get("source")) != pid:
                continue
            target = self.node_by_id.get(str(edge.get("target")))
            if target is None or _node_type(target) != "Song":
                continue
            year = _safe_year(target.get("release_date"))
            if year is None or not (start_year <= year <= end_year):
                continue
            song_ids.append(str(target.get("id")))
            songs.append(target)
            years.add(year)
            if target.get("genre"):
                genre_counts[str(target["genre"])] += 1
            if bool(target.get("notable")):
                notable_n += 1

        for edge in self.links:
            sid = str(edge.get("source"))
            tid = str(edge.get("target"))
            if sid == pid and tid != pid and _node_type(self.node_by_id.get(tid, {})) == "Person":
                collaborators.add(tid)
            elif tid == pid and sid != pid and _node_type(self.node_by_id.get(sid, {})) == "Person":
                collaborators.add(sid)

        degree = sum(1 for edge in self.links if pid in {str(edge.get("source")), str(edge.get("target"))})
        total_songs = len(song_ids)
        notable_rate = round(notable_n / total_songs, 4) if total_songs else 0.0
        genre_entropy = 0.0
        if genre_counts:
            total = sum(genre_counts.values())
            for count in genre_counts.values():
                if count <= 0:
                    continue
                p = count / total
                genre_entropy -= p * math.log(p + 1e-12, 2)
            genre_entropy = round(genre_entropy, 4)

        return {
            "person_id": pid,
            "name": str(person.get("name") or ""),
            "metrics": {
                "song_count": total_songs,
                "notable_rate": notable_rate,
                "active_years": len(years),
                "unique_collaborators": len(collaborators),
                "genre_entropy": genre_entropy,
                "degree": degree,
                "pagerank": round(degree / max(len(self.links), 1), 6),
            },
        }

    def search(self, q: str, type_: str, limit: int) -> list[dict[str, Any]]:
        q = _norm(q)
        if not q:
            return []
        hits: list[dict[str, Any]] = []
        if type_ in {"person", "all"}:
            for node in self.nodes:
                if _node_type(node) != "Person":
                    continue
                name = _norm(_node_name(node))
                stage = _norm(str(node.get("stage_name") or ""))
                if q in name or q in stage:
                    hits.append(
                        {"id": str(node.get("id")), "label": _node_name(node), "type": "person", "subtitle": _node_name(node)}
                    )
                if len(hits) >= limit:
                    return hits[:limit]
        if type_ in {"song", "all"} and len(hits) < limit:
            for node in self.nodes:
                if _node_type(node) != "Song":
                    continue
                name = _norm(_node_name(node))
                if q in name:
                    subtitle = f"{node.get('release_date', '')} · {node.get('genre', '')}"
                    hits.append(
                        {"id": str(node.get("id")), "label": _node_name(node), "type": "song", "subtitle": subtitle}
                    )
                if len(hits) >= limit:
                    return hits[:limit]
        return hits[:limit]


@lru_cache(maxsize=1)
def load_local_graph() -> LocalGraph:
    raw = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    nodes = list(raw.get("nodes", []))
    links = list(raw.get("links", []))

    node_by_id: dict[str, dict[str, Any]] = {}
    node_ids_by_name: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        nid = str(node.get("id"))
        node_by_id[nid] = node
        node_ids_by_name[_norm(_node_name(node))].append(nid)
        stage = str(node.get("stage_name") or "").strip()
        if stage:
            node_ids_by_name[_norm(stage)].append(nid)

    out_edges: dict[str, list[int]] = defaultdict(list)
    in_edges: dict[str, list[int]] = defaultdict(list)
    for idx, edge in enumerate(links):
        sid = str(edge.get("source"))
        tid = str(edge.get("target"))
        out_edges[sid].append(idx)
        in_edges[tid].append(idx)

    return LocalGraph(
        nodes=nodes,
        links=links,
        node_by_id=node_by_id,
        node_ids_by_name=dict(node_ids_by_name),
        out_edges=dict(out_edges),
        in_edges=dict(in_edges),
    )
