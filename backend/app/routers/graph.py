from typing import Any, Literal, Optional, Union, List

from fastapi import APIRouter, HTTPException, Path, Query, Request

from app.schemas.analysis import InfluenceGalaxyData
from app.schemas.common import ApiMeta, ApiResponse
from app.schemas.graph import GraphLink, GraphNode, GraphPayload, SubgraphRequest


router = APIRouter(prefix="/graph", tags=["关系网络"])


# ---- 工具函数 ----

def _public_id(node: Any) -> str:
    raw = node.get("original_id")
    if raw is None:
        raw = node.get("id")
    if raw is not None:
        return str(raw)
    return str(getattr(node, "element_id", ""))


def _infer_label(label_list: Optional[List[str]]) -> str:
    """根据节点标签列表返回标准化的标签名。
    优先级：Person > MusicalGroup > Song > Album > RecordLabel > labels[0] > "Node"。
    """
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


@router.post("/subgraph", response_model=ApiResponse)
async def post_subgraph(request: Request, body: SubgraphRequest):
    driver = getattr(request.app.state, "neo4j_driver", None)
    if driver is None:
        raise HTTPException(status_code=503, detail="数据库连接不可用")

    async with driver.session() as session:
        notable_filter = "AND coalesce(s.notable, false) = true" if body.only_notable_songs else ""
        cypher = f"""
        MATCH (p:Person)-[r]->(s:Song)
        WHERE type(r) IN ['PERFORMER_OF', 'INTERPOLATES_FROM']
          AND toInteger(trim(toString(s.release_date))) >= $sy
          AND toInteger(trim(toString(s.release_date))) <= $ey
          {notable_filter}
          AND (size($genres) = 0 OR s.genre IN $genres)
          AND (size($seed) = 0 OR toString(p.original_id) IN $seed OR toString(p.id) IN $seed OR p.name IN $seed)
        RETURN p, labels(p) AS p_labels, r, s, labels(s) AS s_labels, type(r) as rel_type, properties(r) as rel_props
        LIMIT $lim
        """
        result = await session.run(
            cypher,
            sy=body.start_year,
            ey=body.end_year,
            genres=body.genres,
            seed=[str(x) for x in body.seed_person_ids],
            lim=body.limit_nodes,
        )
        records = await result.data()

        nodes: dict[str, GraphNode] = {}
        links: list[GraphLink] = []

        for row in records:
            p_data, p_labels, rel, s_data, s_labels = row["p"], row["p_labels"], row["r"], row["s"], row["s_labels"]
            rel_type = row.get("rel_type") or ""
            rel_props: dict = row.get("rel_props") or {}
            pn = _graph_node(p_data, _infer_label(p_labels))
            sn = _graph_node(s_data, _infer_label(s_labels))
            nodes[pn.id] = pn
            nodes[sn.id] = sn
            links.append(GraphLink(source=pn.id, target=sn.id, type=rel_type, props=rel_props))

        meta = ApiMeta(
            node_count=len(nodes),
            link_count=len(links),
            truncated=len(records) >= body.limit_nodes,
            db="connected",
        )
        return ApiResponse(
            data=InfluenceGalaxyData(
                graph=GraphPayload(nodes=list(nodes.values()), links=links),
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
):
    driver = getattr(request.app.state, "neo4j_driver", None)
    if driver is None:
        raise HTTPException(status_code=503, detail="数据库连接不可用")

    types = [x.strip() for x in rel_types.split(",")] if rel_types else ["PERFORMER_OF", "IN_STYLE_OF", "INTERPOLATES_FROM"]

    if direction == "out":
        pattern = "(n)-[r]->(m)"
    elif direction == "in":
        pattern = "(n)<-[r]-(m)"
    else:
        pattern = "(n)-[r]-(m)"

    async with driver.session() as session:
        cypher = f"""
        MATCH (n)
        WHERE toString(n.original_id) = $nid OR toString(n.id) = $nid OR n.name = $nid
        WITH n LIMIT 1
        MATCH {pattern}
        WHERE type(r) IN $types
        RETURN n, labels(n) AS n_labels, r, m, labels(m) AS m_labels, type(r) as rel_type, properties(r) as rel_props
        LIMIT $lim
        """
        result = await session.run(cypher, nid=node_id, types=types, lim=limit)
        records = await result.data()

        nodes: dict[str, GraphNode] = {}
        links: list[GraphLink] = []

        for row in records:
            n_data, n_labels, rel, m_data, m_labels = row["n"], row["n_labels"], row["r"], row["m"], row["m_labels"]
            rel_type = row.get("rel_type") or ""
            rel_props: dict = row.get("rel_props") or {}
            nn = _graph_node(n_data, _infer_label(n_labels))
            mn = _graph_node(m_data, _infer_label(m_labels))
            nodes[nn.id] = nn
            nodes[mn.id] = mn
            links.append(GraphLink(
                source=_public_id(rel.start_node),
                target=_public_id(rel.end_node),
                type=rel_type,
                props=rel_props,
            ))

        meta = ApiMeta(
            node_count=len(nodes),
            link_count=len(links),
            truncated=len(records) >= limit,
            db="connected",
        )
        return ApiResponse(
            data=InfluenceGalaxyData(
                graph=GraphPayload(nodes=list(nodes.values()), links=links),
            ),
            meta=meta,
        )
