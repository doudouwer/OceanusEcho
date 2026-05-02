from collections import defaultdict, deque
from typing import Any, Literal, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Request

from app.constants import DEFAULT_REL_TYPES
from app.schemas.analysis import GalaxyBridgeNode, GalaxyCluster, InfluenceGalaxyData, PersonRef
from app.schemas.common import ApiMeta, ApiResponse
from app.schemas.graph import GraphLink, GraphNode, GraphPayload, SubgraphRequest


router = APIRouter(prefix="/graph", tags=["关系网络"])

_PERSON_LIKE = {"Person", "MusicalGroup"}
_SONG_LIKE = {"Song", "Album"}


# ---- 工具函数 ----

def _public_id(node: Any) -> str:
    raw = node.get("original_id")
    if raw is None:
        raw = node.get("id")
    if raw is not None:
        return str(raw)
    return str(getattr(node, "element_id", ""))


def _infer_label(label_list: Optional[list[str]]) -> str:
    """根据节点标签列表返回标准化标签。"""
    if not label_list:
        return "Node"
    for preferred in ("Person", "MusicalGroup", "Song", "Album", "RecordLabel"):
        if preferred in label_list:
            return preferred
    return label_list[0]


def _graph_node(n: Any, label_override: Optional[str] = None) -> GraphNode:
    label = label_override or _infer_label(None)
    props = dict(n)
    pid = _public_id(n)
    name = props.get("name")
    extra = {k: v for k, v in props.items() if k not in ("id", "original_id", "name")}
    return GraphNode(id=pid, label=label, name=str(name) if name is not None else None, props=extra)


def _resolve_rel_types(raw_types: list[str]) -> list[str]:
    if not raw_types:
        return list(DEFAULT_REL_TYPES.values())

    allowed = set(DEFAULT_REL_TYPES.values())
    resolved: list[str] = []
    seen: set[str] = set()
    for raw in raw_types:
        key = str(raw).strip()
        if not key:
            continue
        key_up = key.upper()
        neo_type = DEFAULT_REL_TYPES.get(key_up, key_up)
        if neo_type in allowed and neo_type not in seen:
            seen.add(neo_type)
            resolved.append(neo_type)
    return resolved or list(DEFAULT_REL_TYPES.values())


def _parse_csv(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def _build_adjacency(links: list[GraphLink]) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = defaultdict(set)
    for link in links:
        s = str(link.source)
        t = str(link.target)
        if not s or not t or s == t:
            continue
        adj[s].add(t)
        adj[t].add(s)
    return adj


def _apply_seed_hops(
    nodes: dict[str, GraphNode],
    links: list[GraphLink],
    seed_values: set[str],
    max_hops: int,
) -> tuple[dict[str, GraphNode], list[GraphLink], list[str]]:
    if not seed_values:
        return nodes, links, []

    seed_node_ids: list[str] = []
    for nid, node in nodes.items():
        if node.label not in _PERSON_LIKE:
            continue
        if nid in seed_values or (node.name and node.name in seed_values):
            seed_node_ids.append(nid)

    if not seed_node_ids:
        return {}, [], []

    adj = _build_adjacency(links)
    selected: set[str] = set(seed_node_ids)
    queue: deque[tuple[str, int]] = deque((sid, 0) for sid in seed_node_ids)

    while queue:
        cur, depth = queue.popleft()
        if depth >= max_hops:
            continue
        for nxt in adj.get(cur, set()):
            if nxt in selected:
                continue
            selected.add(nxt)
            queue.append((nxt, depth + 1))

    kept_nodes = {nid: node for nid, node in nodes.items() if nid in selected}
    kept_links = [lk for lk in links if str(lk.source) in selected and str(lk.target) in selected]
    return kept_nodes, kept_links, seed_node_ids


def _trim_by_limit(nodes: dict[str, GraphNode], links: list[GraphLink], limit_nodes: int, seed_ids: set[str]) -> tuple[dict[str, GraphNode], list[GraphLink]]:
    if len(nodes) <= limit_nodes:
        return nodes, links

    adj = _build_adjacency(links)

    def score(nid: str) -> tuple[int, int, int]:
        node = nodes[nid]
        is_seed = 1 if nid in seed_ids else 0
        is_person = 1 if node.label in _PERSON_LIKE else 0
        degree = len(adj.get(nid, set()))
        return (is_seed, degree, is_person)

    ordered = sorted(nodes.keys(), key=score, reverse=True)
    keep = set(ordered[:limit_nodes])

    kept_nodes = {nid: n for nid, n in nodes.items() if nid in keep}
    kept_links = [lk for lk in links if str(lk.source) in keep and str(lk.target) in keep]
    return kept_nodes, kept_links


def _person_projection(nodes: dict[str, GraphNode], links: list[GraphLink]) -> dict[str, set[str]]:
    person_ids = {nid for nid, n in nodes.items() if n.label in _PERSON_LIKE}
    if not person_ids:
        return {}

    person_adj: dict[str, set[str]] = defaultdict(set)
    song_to_people: dict[str, set[str]] = defaultdict(set)

    for link in links:
        s = str(link.source)
        t = str(link.target)
        s_label = nodes.get(s).label if s in nodes else None
        t_label = nodes.get(t).label if t in nodes else None

        if s in person_ids and t in person_ids:
            person_adj[s].add(t)
            person_adj[t].add(s)
            continue

        if s in person_ids and t_label in _SONG_LIKE:
            song_to_people[t].add(s)
        elif t in person_ids and s_label in _SONG_LIKE:
            song_to_people[s].add(t)

    for _, people in song_to_people.items():
        plist = list(people)
        for i in range(len(plist)):
            for j in range(i + 1, len(plist)):
                a = plist[i]
                b = plist[j]
                person_adj[a].add(b)
                person_adj[b].add(a)

    for pid in person_ids:
        person_adj.setdefault(pid, set())

    return person_adj


def _connected_components(adj: dict[str, set[str]]) -> list[list[str]]:
    seen: set[str] = set()
    comps: list[list[str]] = []

    for node in adj:
        if node in seen:
            continue
        queue = deque([node])
        seen.add(node)
        comp: list[str] = []
        while queue:
            cur = queue.popleft()
            comp.append(cur)
            for nxt in adj.get(cur, set()):
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        comps.append(comp)

    comps.sort(key=len, reverse=True)
    return comps


def _articulation_points(adj: dict[str, set[str]]) -> set[str]:
    disc: dict[str, int] = {}
    low: dict[str, int] = {}
    parent: dict[str, Optional[str]] = {}
    art: set[str] = set()
    time = 0

    def dfs(u: str) -> None:
        nonlocal time
        time += 1
        disc[u] = time
        low[u] = time
        child_cnt = 0

        for v in adj.get(u, set()):
            if v not in disc:
                parent[v] = u
                child_cnt += 1
                dfs(v)
                low[u] = min(low[u], low[v])

                if parent.get(u) is None and child_cnt > 1:
                    art.add(u)
                if parent.get(u) is not None and low[v] >= disc[u]:
                    art.add(u)
            elif v != parent.get(u):
                low[u] = min(low[u], disc[v])

    for node in adj:
        if node not in disc:
            parent[node] = None
            dfs(node)

    return art


def _bridge_score(node: str, adj: dict[str, set[str]], is_articulation: bool) -> float:
    neighbors = list(adj.get(node, set()))
    deg = len(neighbors)
    if deg == 0:
        return 0.0
    if deg == 1:
        return round(1.2 + (1.0 if is_articulation else 0.0), 4)

    edges_among_neighbors = 0
    for i in range(len(neighbors)):
        ni = neighbors[i]
        nset = adj.get(ni, set())
        for j in range(i + 1, len(neighbors)):
            nj = neighbors[j]
            if nj in nset:
                edges_among_neighbors += 1

    possible = deg * (deg - 1) / 2
    clustering = edges_among_neighbors / possible if possible > 0 else 0.0
    local_bridging = 1.0 - clustering
    score = local_bridging * deg + (1.5 if is_articulation else 0.0)
    return round(score, 4)


def _community_summary(nodes: dict[str, GraphNode], links: list[GraphLink]) -> tuple[list[GalaxyCluster], list[GalaxyBridgeNode], dict[str, int]]:
    proj = _person_projection(nodes, links)
    if not proj:
        return [], [], {}

    comps = _connected_components(proj)
    comp_map: dict[str, int] = {}
    for idx, comp in enumerate(comps, start=1):
        for nid in comp:
            comp_map[nid] = idx

    clusters: list[GalaxyCluster] = []
    for idx, comp in enumerate(comps, start=1):
        comp_set = set(comp)
        edge_count = 0
        for nid in comp:
            edge_count += sum(1 for nbr in proj.get(nid, set()) if nbr in comp_set)
        edge_count //= 2

        ranked_people = sorted(comp, key=lambda nid: len(proj.get(nid, set())), reverse=True)
        samples = [
            PersonRef(id=nid, name=nodes[nid].name or nid)
            for nid in ranked_people[: min(5, len(ranked_people))]
        ]
        clusters.append(
            GalaxyCluster(
                component_id=idx,
                node_count=len(comp),
                edge_count=edge_count,
                sample_nodes=samples,
            )
        )

    arts = _articulation_points(proj)
    bridges: list[GalaxyBridgeNode] = []
    for nid, nbrs in proj.items():
        deg = len(nbrs)
        if deg == 0:
            continue
        score = _bridge_score(nid, proj, nid in arts)
        if score <= 0:
            continue
        node = nodes.get(nid)
        if node is None:
            continue
        bridges.append(
            GalaxyBridgeNode(
                node_id=nid,
                name=node.name or nid,
                label=node.label,
                bridge_score=score,
                degree=deg,
            )
        )

    bridges.sort(key=lambda x: (x.bridge_score, x.degree), reverse=True)
    return clusters, bridges[:10], comp_map


def _decorate_cluster_id(nodes: dict[str, GraphNode], comp_map: dict[str, int]) -> None:
    for nid, component_id in comp_map.items():
        node = nodes.get(nid)
        if node is None:
            continue
        node.props["cluster_id"] = component_id


@router.post("/subgraph", response_model=ApiResponse)
async def post_subgraph(request: Request, body: SubgraphRequest):
    driver = getattr(request.app.state, "neo4j_driver", None)
    if driver is None:
        raise HTTPException(status_code=503, detail="数据库连接不可用")

    rel_types = _resolve_rel_types(body.rel_types)
    seed_values = {str(x) for x in body.seed_person_ids if str(x).strip()}
    rel_limit = min(max(body.limit_nodes * 8, 1500), 120_000)

    async with driver.session() as session:
        if seed_values:
            cypher = f"""
            MATCH (seed)
            WHERE (seed:Person OR seed:MusicalGroup)
              AND (toString(seed.original_id) IN $seeds OR seed.name IN $seeds)
            MATCH path=(seed)-[rels*1..{body.max_hops}]-(neighbor)
            WHERE all(r IN rels WHERE type(r) IN $rel_types)
            WITH path, rels
            LIMIT $path_lim
            UNWIND range(0, size(rels) - 1) AS idx
            WITH nodes(path)[idx] AS a,
                 labels(nodes(path)[idx]) AS a_labels,
                 nodes(path)[idx + 1] AS b,
                 labels(nodes(path)[idx + 1]) AS b_labels,
                 rels[idx] AS r
            WHERE (
              NOT (a:Song OR b:Song)
              OR (
                a:Song
                AND toInteger(trim(toString(a.release_date))) >= $sy
                AND toInteger(trim(toString(a.release_date))) <= $ey
                AND (size($genres) = 0 OR a.genre IN $genres)
                AND ($only_notable = false OR coalesce(a.notable, false) = true)
              )
              OR (
                b:Song
                AND toInteger(trim(toString(b.release_date))) >= $sy
                AND toInteger(trim(toString(b.release_date))) <= $ey
                AND (size($genres) = 0 OR b.genre IN $genres)
                AND ($only_notable = false OR coalesce(b.notable, false) = true)
              )
            )
            RETURN a, a_labels, b, b_labels, type(r) AS rel_type, properties(r) AS rel_props
            LIMIT $lim
            """
            result = await session.run(
                cypher,
                seeds=list(seed_values),
                rel_types=rel_types,
                sy=body.start_year,
                ey=body.end_year,
                genres=body.genres,
                only_notable=body.only_notable_songs,
                path_lim=rel_limit,
                lim=rel_limit,
            )
        else:
            cypher = """
            MATCH (a)-[r]->(b)
            WHERE type(r) IN $rel_types
              AND (
                (
                  a:Song
                  AND toInteger(trim(toString(a.release_date))) >= $sy
                  AND toInteger(trim(toString(a.release_date))) <= $ey
                  AND (size($genres) = 0 OR a.genre IN $genres)
                  AND ($only_notable = false OR coalesce(a.notable, false) = true)
                )
                OR
                (
                  b:Song
                  AND toInteger(trim(toString(b.release_date))) >= $sy
                  AND toInteger(trim(toString(b.release_date))) <= $ey
                  AND (size($genres) = 0 OR b.genre IN $genres)
                  AND ($only_notable = false OR coalesce(b.notable, false) = true)
                )
                OR
                (
                  NOT a:Song AND NOT b:Song
                  AND (
                    EXISTS {
                      MATCH (a)-[]-(sa:Song)
                      WHERE toInteger(trim(toString(sa.release_date))) >= $sy
                        AND toInteger(trim(toString(sa.release_date))) <= $ey
                        AND (size($genres) = 0 OR sa.genre IN $genres)
                        AND ($only_notable = false OR coalesce(sa.notable, false) = true)
                    }
                    OR EXISTS {
                      MATCH (b)-[]-(sb:Song)
                      WHERE toInteger(trim(toString(sb.release_date))) >= $sy
                        AND toInteger(trim(toString(sb.release_date))) <= $ey
                        AND (size($genres) = 0 OR sb.genre IN $genres)
                        AND ($only_notable = false OR coalesce(sb.notable, false) = true)
                    }
                  )
                )
              )
            RETURN a, labels(a) AS a_labels, b, labels(b) AS b_labels, type(r) AS rel_type, properties(r) AS rel_props
            LIMIT $lim
            """
            result = await session.run(
                cypher,
                rel_types=rel_types,
                sy=body.start_year,
                ey=body.end_year,
                genres=body.genres,
                only_notable=body.only_notable_songs,
                lim=rel_limit,
            )
        rows = await result.data()

    nodes: dict[str, GraphNode] = {}
    links: list[GraphLink] = []
    link_seen: set[tuple[str, str, str]] = set()

    for row in rows:
        a_data = row["a"]
        b_data = row["b"]
        a_labels = row["a_labels"]
        b_labels = row["b_labels"]
        rel_type = row.get("rel_type") or ""
        rel_props = row.get("rel_props") or {}

        na = _graph_node(a_data, _infer_label(a_labels))
        nb = _graph_node(b_data, _infer_label(b_labels))
        nodes[na.id] = na
        nodes[nb.id] = nb

        key = (na.id, nb.id, rel_type)
        if key in link_seen:
            continue
        link_seen.add(key)
        links.append(GraphLink(source=na.id, target=nb.id, type=rel_type, props=rel_props))

    raw_node_count = len(nodes)
    raw_link_count = len(links)

    if seed_values:
        seed_node_ids = [
            nid for nid, node in nodes.items()
            if node.label in _PERSON_LIKE and (nid in seed_values or (node.name and node.name in seed_values))
        ]
    else:
        nodes, links, seed_node_ids = _apply_seed_hops(nodes, links, seed_values, body.max_hops)

    if nodes:
        nodes, links = _trim_by_limit(nodes, links, body.limit_nodes, set(seed_node_ids))

    clusters, bridge_nodes, comp_map = _community_summary(nodes, links)
    _decorate_cluster_id(nodes, comp_map)

    seed_people = [
        PersonRef(id=sid, name=nodes[sid].name or sid)
        for sid in seed_node_ids
        if sid in nodes
    ]

    truncated = (
        len(rows) >= rel_limit
        or raw_node_count > len(nodes)
        or raw_link_count > len(links)
    )

    meta = ApiMeta(
        node_count=len(nodes),
        link_count=len(links),
        truncated=truncated,
        db="connected",
    )
    return ApiResponse(
        data=InfluenceGalaxyData(
            graph=GraphPayload(nodes=list(nodes.values()), links=links),
            seed_people=seed_people,
            clusters=clusters,
            bridge_nodes=bridge_nodes,
        ),
        meta=meta,
    )


@router.get("/expand/{node_id}", response_model=ApiResponse)
async def get_expand(
    request: Request,
    node_id: str = Path(..., description="节点 ID（original_id 或 name）"),
    rel_types: Optional[str] = Query(None, description="逗号分隔，如 PERFORMER_OF,IN_STYLE_OF"),
    direction: Literal["out", "in", "both"] = "both",
    limit: int = Query(200, ge=1, le=5000),
    start_year: Optional[int] = Query(None, ge=1900, le=2200),
    end_year: Optional[int] = Query(None, ge=1900, le=2200),
    genres: Optional[str] = Query(None, description="逗号分隔流派，如 Oceanus Folk,Indie Pop"),
    only_notable_songs: bool = Query(False),
):
    driver = getattr(request.app.state, "neo4j_driver", None)
    if driver is None:
        raise HTTPException(status_code=503, detail="数据库连接不可用")

    if start_year is not None and end_year is not None and end_year < start_year:
        raise HTTPException(status_code=400, detail="end_year must be >= start_year")

    types = _resolve_rel_types(_parse_csv(rel_types))
    genre_list = _parse_csv(genres)

    if direction == "out":
        pattern = "(n)-[r]->(m)"
    elif direction == "in":
        pattern = "(n)<-[r]-(m)"
    else:
        pattern = "(n)-[r]-(m)"

    async with driver.session() as session:
        cypher = f"""
        MATCH (n)
        WHERE toString(n.original_id) = $nid OR n.name = $nid
        WITH n LIMIT 1
        MATCH {pattern}
        WHERE type(r) IN $types
          AND (
            NOT (n:Song OR m:Song)
            OR (
              (
                n:Song
                AND ($sy IS NULL OR toInteger(trim(toString(n.release_date))) >= $sy)
                AND ($ey IS NULL OR toInteger(trim(toString(n.release_date))) <= $ey)
                AND (size($genres) = 0 OR n.genre IN $genres)
                AND ($only_notable = false OR coalesce(n.notable, false) = true)
              )
              OR
              (
                m:Song
                AND ($sy IS NULL OR toInteger(trim(toString(m.release_date))) >= $sy)
                AND ($ey IS NULL OR toInteger(trim(toString(m.release_date))) <= $ey)
                AND (size($genres) = 0 OR m.genre IN $genres)
                AND ($only_notable = false OR coalesce(m.notable, false) = true)
              )
            )
          )
        RETURN n, labels(n) AS n_labels, m, labels(m) AS m_labels,
               type(r) as rel_type, properties(r) as rel_props,
               coalesce(toString(startNode(r).original_id), elementId(startNode(r))) AS rel_source,
               coalesce(toString(endNode(r).original_id), elementId(endNode(r))) AS rel_target
        LIMIT $lim
        """
        result = await session.run(
            cypher,
            nid=node_id,
            types=types,
            lim=limit,
            sy=start_year,
            ey=end_year,
            genres=genre_list,
            only_notable=only_notable_songs,
        )
        rows = await result.data()

    nodes: dict[str, GraphNode] = {}
    links: list[GraphLink] = []
    seen: set[tuple[str, str, str]] = set()

    for row in rows:
        n_data = row["n"]
        m_data = row["m"]
        n_labels = row["n_labels"]
        m_labels = row["m_labels"]
        rel_type = row.get("rel_type") or ""
        rel_props = row.get("rel_props") or {}

        nn = _graph_node(n_data, _infer_label(n_labels))
        mn = _graph_node(m_data, _infer_label(m_labels))
        nodes[nn.id] = nn
        nodes[mn.id] = mn

        rel_source = str(row.get("rel_source") or "")
        rel_target = str(row.get("rel_target") or "")
        key = (rel_source, rel_target, rel_type)
        if key in seen:
            continue
        seen.add(key)
        links.append(
            GraphLink(
                source=key[0],
                target=key[1],
                type=rel_type,
                props=rel_props,
            )
        )

    meta = ApiMeta(
        node_count=len(nodes),
        link_count=len(links),
        truncated=len(rows) >= limit,
        db="connected",
    )
    return ApiResponse(
        data=InfluenceGalaxyData(
            graph=GraphPayload(nodes=list(nodes.values()), links=links),
            clusters=[],
            bridge_nodes=[],
        ),
        meta=meta,
    )
