from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from app.core.database import get_neo4j_connection
from app.schemas.analysis import GalaxyBridgeNode, GalaxyCluster, InfluenceGalaxyData, PersonRef
from app.schemas.graph import GraphLink, GraphNode, GraphPayload
from app.services.local_graph import load_local_graph
from app.services.neo4j_serialize import graph_link_from_neo, graph_node_from_neo, node_public_id


LOCAL_GRAPH = load_local_graph()


def _cluster_summary(nodes: list[GraphNode], links: list[GraphLink]) -> tuple[list[GalaxyCluster], list[GalaxyBridgeNode]]:
    if not nodes:
        return [], []

    adj: dict[str, set[str]] = defaultdict(set)
    for link in links:
        adj[link.source].add(link.target)
        adj[link.target].add(link.source)

    node_labels = {node.id: node.label for node in nodes}
    seen: set[str] = set()
    clusters: list[GalaxyCluster] = []
    for node in nodes:
        if node.id in seen:
            continue
        stack = [node.id]
        component: list[str] = []
        seen.add(node.id)
        while stack:
            current = stack.pop()
            component.append(current)
            for nxt in adj.get(current, set()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        comp_set = set(component)
        edge_count = sum(1 for link in links if link.source in comp_set and link.target in comp_set)
        sample_nodes = [
            PersonRef(id=node_id, name=(next((n.name for n in nodes if n.id == node_id), "")))
            for node_id in component
            if node_labels.get(node_id) == "Person"
        ][:3]
        clusters.append(
            GalaxyCluster(
                component_id=len(clusters) + 1,
                node_count=len(component),
                edge_count=edge_count,
                sample_nodes=sample_nodes,
            )
        )

    degree: dict[str, int] = defaultdict(int)
    for link in links:
        degree[link.source] += 1
        degree[link.target] += 1
    bridge_candidates = sorted(nodes, key=lambda n: (-degree.get(n.id, 0), n.label, n.name or "", n.id))
    bridge_nodes = [
        GalaxyBridgeNode(
            node_id=node.id,
            name=node.name or "",
            label=node.label,
            bridge_score=round(degree.get(node.id, 0) / max(len(links), 1), 6),
            degree=degree.get(node.id, 0),
        )
        for node in bridge_candidates[:10]
    ]
    return clusters, bridge_nodes


class InfluenceGalaxyService:
    def __init__(self) -> None:
        self.db = get_neo4j_connection()

    def get_subgraph(
        self,
        start_year: int,
        end_year: int,
        genres: list[str],
        seed_person_ids: list[str],
        rel_types: list[str],
        limit_nodes: int,
        only_notable_songs: bool,
    ) -> InfluenceGalaxyData:
        with self.db.session() as session:
            if session is None:
                nodes, links, _meta = LOCAL_GRAPH.subgraph(
                    start_year,
                    end_year,
                    genres,
                    seed_person_ids,
                    rel_types,
                    limit_nodes,
                    only_notable_songs,
                )
                graph = GraphPayload(nodes=nodes, links=links)
                seed_people = []
                for pid in seed_person_ids:
                    node = LOCAL_GRAPH.resolve_person(pid, None) or LOCAL_GRAPH.resolve_node(pid)
                    if node is not None:
                        seed_people.append(PersonRef(id=str(node.get("id")), name=str(node.get("name") or "")))
                    else:
                        seed_people.append(PersonRef(id=pid, name=pid))
                clusters, bridge_nodes = _cluster_summary(nodes, links)
                return InfluenceGalaxyData(
                    graph=graph,
                    seed_people=seed_people,
                    clusters=clusters,
                    bridge_nodes=bridge_nodes,
                )

            rel_set = {r.strip() for r in rel_types if r.strip()} or {"PERFORMER_OF", "IN_STYLE_OF"}
            notable_filter = "AND (NOT (a:Song OR a:Album) OR coalesce(a.notable, false) = true)" if only_notable_songs else ""
            notable_filter_b = "AND (NOT (b:Song OR b:Album) OR coalesce(b.notable, false) = true)" if only_notable_songs else ""
            genre_filter_a = "AND (size($genres) = 0 OR a.genre IN $genres)" if genres else ""
            genre_filter_b = "AND (size($genres) = 0 OR b.genre IN $genres)" if genres else ""
            cypher = f"""
            MATCH (a)-[r]->(b)
            WHERE type(r) IN $types
              AND (
                size($seed) = 0
                OR toString(a.original_id) IN $seed OR a.name IN $seed OR toString(b.original_id) IN $seed OR b.name IN $seed
              )
              AND (
                NOT (a:Song OR a:Album)
                OR (
                  toInteger(trim(toString(a.release_date))) >= $sy
                  AND toInteger(trim(toString(a.release_date))) <= $ey
                  {genre_filter_a}
                  {notable_filter}
                )
              )
              AND (
                NOT (b:Song OR b:Album)
                OR (
                  toInteger(trim(toString(b.release_date))) >= $sy
                  AND toInteger(trim(toString(b.release_date))) <= $ey
                  {genre_filter_b}
                  {notable_filter_b}
                )
              )
            RETURN a, r, b
            LIMIT $lim
            """
            rows = list(
                session.run(
                    cypher,
                    sy=start_year,
                    ey=end_year,
                    genres=genres,
                    seed=seed_person_ids,
                    types=list(rel_set),
                    lim=limit_nodes,
                )
            )
            nodes: dict[str, GraphNode] = {}
            links: list[GraphLink] = []
            for row in rows:
                a, r, b = row["a"], row["r"], row["b"]
                an = graph_node_from_neo(a)
                bn = graph_node_from_neo(b)
                nodes[an.id] = an
                nodes[bn.id] = bn
                links.append(graph_link_from_neo(an.id, bn.id, r))

            graph = GraphPayload(nodes=list(nodes.values()), links=links)
            seed_people = []
            for pid in seed_person_ids:
                node = LOCAL_GRAPH.resolve_person(pid, None) or LOCAL_GRAPH.resolve_node(pid)
                if node is not None:
                    seed_people.append(PersonRef(id=node_public_id(node), name=str(node.get("name") or "")))
                else:
                    seed_people.append(PersonRef(id=pid, name=pid))
            clusters, bridge_nodes = _cluster_summary(graph.nodes, graph.links)
            return InfluenceGalaxyData(
                graph=graph,
                seed_people=seed_people,
                clusters=clusters,
                bridge_nodes=bridge_nodes,
            )

    def expand(
        self,
        node_id: str,
        rel_types: str | None,
        direction: str,
        limit: int,
    ) -> GraphPayload:
        with self.db.session() as session:
            if session is None:
                nodes, links, _meta = LOCAL_GRAPH.expand(
                    node_id,
                    [x.strip() for x in rel_types.split(",")] if rel_types else None,
                    direction,
                    limit,
                )
                return GraphPayload(nodes=nodes, links=links)

            types = [x.strip() for x in rel_types.split(",")] if rel_types else ["PERFORMER_OF", "IN_STYLE_OF"]
            if direction == "out":
                pattern = "(n)-[r]->(m)"
            elif direction == "in":
                pattern = "(n)<-[r]-(m)"
            else:
                pattern = "(n)-[r]-(m)"

            cypher = f"""
            MATCH (n)
            WHERE toString(n.original_id) = $nid OR toString(n.id) = $nid OR n.name = $nid
            WITH n LIMIT 1
            MATCH {pattern}
            WHERE type(r) IN $types
            RETURN n, r, m
            LIMIT $lim
            """
            rows = list(session.run(cypher, nid=node_id, types=types, lim=limit))
            nodes: dict[str, GraphNode] = {}
            links: list[GraphLink] = []
            for row in rows:
                n, r, m = row["n"], row["r"], row["m"]
                nn = graph_node_from_neo(n)
                mn = graph_node_from_neo(m)
                nodes[nn.id] = nn
                nodes[mn.id] = mn
                links.append(graph_link_from_neo(node_public_id(r.start_node), node_public_id(r.end_node), r))
            return GraphPayload(nodes=list(nodes.values()), links=links)


influence_galaxy_service = InfluenceGalaxyService()
