from neo4j.graph import Node, Relationship

from app.schemas.graph import GraphLink, GraphNode


def node_public_id(n: Node) -> str:
    raw = n.get("id")
    if raw is not None:
        return str(raw)
    return str(n.element_id)


def graph_node_from_neo(n: Node) -> GraphNode:
    label = next(iter(n.labels), "Node")
    props = dict(n)
    pid = node_public_id(n)
    name = props.get("name")
    extra = {k: v for k, v in props.items() if k not in ("id", "name")}
    return GraphNode(id=pid, label=label, name=str(name) if name is not None else None, props=extra)


def graph_link_from_neo(source_id: str, target_id: str, rel: Relationship) -> GraphLink:
    return GraphLink(
        source=source_id,
        target=target_id,
        type=rel.type,
        props={k: v for k, v in dict(rel).items()},
    )
