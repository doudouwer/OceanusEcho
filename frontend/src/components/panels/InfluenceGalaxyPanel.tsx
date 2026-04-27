import ForceGraph2D from "react-force-graph-2d";
import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  fetchInfluenceExpand,
  fetchInfluenceSubgraph,
  type InfluenceGalaxyPayload,
} from "@/api/oceanus";
import { useDashboardStore } from "@/store/dashboardStore";
import { PanelCard } from "@/components/panels/PanelCard";
import panelStyles from "@/components/panels/PanelCard.module.css";

type GraphNode = { id: string; name: string; group: string; clusterId?: number };
type GraphLink = { source: string | { id: string }; target: string | { id: string }; type: string };

type GraphData = { nodes: GraphNode[]; links: GraphLink[] };

const REL_TYPES = [
  "IN_STYLE_OF",
  "INTERPOLATES_FROM",
  "PERFORMER_OF",
  "COMPOSER_OF",
  "LYRICIST_OF",
  "PRODUCER_OF",
  "MEMBER_OF",
];

const CLUSTER_COLORS = [
  "#5ad8e8",
  "#72c68f",
  "#f0b35f",
  "#e88787",
  "#b99bf5",
  "#89b6ff",
  "#f08cc0",
  "#9ecf5a",
];

const REL_COLORS: Record<string, string> = {
  IN_STYLE_OF: "rgba(245, 140, 184, 0.55)",
  INTERPOLATES_FROM: "rgba(240, 179, 95, 0.55)",
  MEMBER_OF: "rgba(157, 199, 255, 0.55)",
};

function endpointId(v: string | { id: string }): string {
  if (typeof v === "string") return v;
  return v?.id ?? "";
}

function payloadToForceGraph(payload: InfluenceGalaxyPayload): GraphData {
  const nodes = payload.graph.nodes.map((n) => ({
    id: n.id,
    name: (n.name && String(n.name).trim()) || n.id,
    group: n.label,
    clusterId:
      typeof n.props?.cluster_id === "number" && Number.isFinite(n.props.cluster_id)
        ? n.props.cluster_id
        : undefined,
  }));
  const links = payload.graph.links.map((l) => ({
    source: l.source,
    target: l.target,
    type: l.type,
  }));
  return { nodes, links };
}

function mergeGraph(base: GraphData, extra: GraphData): GraphData {
  const nodeMap = new Map<string, GraphNode>();
  for (const n of base.nodes) nodeMap.set(n.id, n);
  for (const n of extra.nodes) nodeMap.set(n.id, n);

  const linkMap = new Map<string, GraphLink>();
  for (const l of base.links) {
    const s = endpointId(l.source);
    const t = endpointId(l.target);
    if (!s || !t) continue;
    linkMap.set(`${s}|${t}|${l.type}`, { source: s, target: t, type: l.type });
  }
  for (const l of extra.links) {
    const s = endpointId(l.source);
    const t = endpointId(l.target);
    if (!s || !t) continue;
    linkMap.set(`${s}|${t}|${l.type}`, { source: s, target: t, type: l.type });
  }

  return { nodes: [...nodeMap.values()], links: [...linkMap.values()] };
}

function isSongLikeLabel(label: string) {
  return label === "Song" || label === "Album";
}

function isPersonLikeLabel(label: string) {
  return label === "Person" || label === "MusicalGroup";
}

function colorForNode(node: GraphNode, focusedPersonId: string | null): string {
  if (isSongLikeLabel(node.group)) return "#7a9aa8";
  if (focusedPersonId != null && node.id === focusedPersonId) return "#5ad8e8";
  if (node.clusterId != null && node.clusterId > 0) {
    return CLUSTER_COLORS[(node.clusterId - 1) % CLUSTER_COLORS.length];
  }
  return "#3a7d8c";
}

export function InfluenceGalaxyPanel() {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 640, h: 320 });
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [expandedNodeIds, setExpandedNodeIds] = useState<string[]>([]);
  const [expandError, setExpandError] = useState<string | null>(null);
  const [expandingNodeId, setExpandingNodeId] = useState<string | null>(null);

  useLayoutEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const measure = () => {
      const w = el.clientWidth;
      const h = Math.max(240, el.clientHeight);
      if (w > 0 && h > 0) setSize({ w, h });
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const focusedPersonId = useDashboardStore((s) => s.focusedPersonId);
  const setFocusedPersonId = useDashboardStore((s) => s.setFocusedPersonId);
  const focusedTimeRange = useDashboardStore((s) => s.focusedTimeRange);
  const yearRange = useDashboardStore((s) => s.yearRange);
  const selectedGenres = useDashboardStore((s) => s.selectedGenres);

  const [ys, ye] = focusedTimeRange ?? yearRange;

  const { data, isPending, isError, error } = useQuery({
    queryKey: [
      "influence-subgraph",
      ys,
      ye,
      selectedGenres.join("|"),
      focusedPersonId ?? "",
      REL_TYPES.join("|"),
    ],
    queryFn: () =>
      fetchInfluenceSubgraph({
        start_year: ys,
        end_year: ye,
        genres: selectedGenres,
        seed_person_ids: focusedPersonId ? [focusedPersonId] : [],
        rel_types: REL_TYPES,
        max_hops: 2,
        limit_nodes: 500,
        only_notable_songs: false,
      }),
  });

  useEffect(() => {
    if (!data?.graph?.nodes?.length) {
      setGraphData({ nodes: [], links: [] });
      setExpandedNodeIds([]);
      return;
    }
    setGraphData(payloadToForceGraph(data));
    setExpandedNodeIds([]);
    setExpandError(null);
    setExpandingNodeId(null);
  }, [data]);

  const onExpand = useCallback(
    async (node: GraphNode) => {
      if (expandedNodeIds.includes(node.id) || expandingNodeId === node.id) return;
      setExpandError(null);
      setExpandingNodeId(node.id);
      try {
        const extra = await fetchInfluenceExpand({
          node_id: node.id,
          rel_types: REL_TYPES,
          direction: "both",
          limit: 180,
          start_year: ys,
          end_year: ye,
          genres: selectedGenres,
          only_notable_songs: false,
        });
        const extraGraph = payloadToForceGraph(extra);
        setGraphData((prev) => mergeGraph(prev, extraGraph));
        setExpandedNodeIds((prev) => [...prev, node.id]);
      } catch (e) {
        setExpandError(e instanceof Error ? e.message : "Expand failed");
      } finally {
        setExpandingNodeId(null);
      }
    },
    [expandedNodeIds, expandingNodeId, ys, ye, selectedGenres],
  );

  const paintNode = useCallback(
    (node: object, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const n = node as GraphNode & { x?: number; y?: number };
      if (n.x == null || n.y == null) return;
      const label = n.name;
      const isFocus = focusedPersonId != null && n.id === focusedPersonId;
      const r = (isSongLikeLabel(n.group) ? 4 : 7) / globalScale;
      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, 2 * Math.PI, false);
      ctx.fillStyle = colorForNode(n, focusedPersonId);
      ctx.fill();
      if (isFocus) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, (r + 2 / globalScale) * 1.1, 0, 2 * Math.PI, false);
        ctx.strokeStyle = "rgba(90,216,232,0.65)";
        ctx.lineWidth = 1.2 / globalScale;
        ctx.stroke();
      }
      if (globalScale > 0.35) {
        ctx.font = `${10 / globalScale}px sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillStyle = "rgba(230,242,245,0.85)";
        ctx.fillText(label, n.x, n.y + r + 2 / globalScale);
      }
    },
    [focusedPersonId],
  );

  const subtitle =
    focusedTimeRange != null
      ? `Brushed range: ${focusedTimeRange[0]}–${focusedTimeRange[1]} · POST /graph/subgraph + GET /graph/expand/{id}`
      : `Global year window: ${yearRange[0]}–${yearRange[1]} · POST /graph/subgraph + GET /graph/expand/{id}`;

  const bridgeHint = useMemo(() => {
    const top = data?.bridge_nodes?.slice(0, 3) ?? [];
    if (!top.length) return "No bridge-node ranking in current subgraph";
    return `Top bridge nodes: ${top.map((x) => `${x.name}(${x.bridge_score.toFixed(2)})`).join(" · ")}`;
  }, [data]);

  const statusLine = isPending
    ? "Loading subgraph…"
    : isError
      ? error instanceof Error
        ? error.message
        : "Failed to load"
      : `${graphData.nodes.length} nodes · ${graphData.links.length} edges · ${data?.clusters?.length ?? 0} communities`;

  return (
    <PanelCard
      title="Influence network"
      tag="Influence Galaxy"
      description="Impact tracing + collaboration map + community structure. Click Person/MusicalGroup to refocus and expand neighbors."
    >
      <p style={{ margin: "0 0.5rem", fontSize: "0.75rem", color: "var(--text-muted)" }}>{subtitle}</p>
      <p style={{ margin: "0 0.5rem 0.25rem", fontSize: "0.7rem", color: "var(--text-muted)" }}>{statusLine}</p>
      {!isPending && !isError && (
        <p style={{ margin: "0 0.5rem 0.25rem", fontSize: "0.68rem", color: "var(--text-muted)" }}>
          {bridgeHint}
          {expandingNodeId ? ` · expanding ${expandingNodeId}...` : ""}
          {expandError ? ` · ${expandError}` : ""}
        </p>
      )}
      <div ref={wrapRef} className={panelStyles.chart} style={{ minHeight: 280 }}>
        {isPending ? (
          <div className={panelStyles.empty}>Loading subgraph…</div>
        ) : isError ? (
          <div className={panelStyles.empty}>{statusLine}</div>
        ) : graphData.nodes.length === 0 ? (
          <div className={panelStyles.empty}>Subgraph is empty; try another year window, genres, or lead person.</div>
        ) : (
          <ForceGraph2D
            graphData={graphData}
            width={size.w}
            height={size.h}
            nodeLabel="name"
            nodeCanvasObject={paintNode}
            nodePointerAreaPaint={(node, color, ctx, globalScale) => {
              const n = node as GraphNode & { x?: number; y?: number };
              if (n.x == null || n.y == null) return;
              const r = (isSongLikeLabel(n.group) ? 6 : 10) / globalScale;
              ctx.fillStyle = color;
              ctx.beginPath();
              ctx.arc(n.x, n.y, r, 0, 2 * Math.PI, false);
              ctx.fill();
            }}
            linkColor={(link) => {
              const l = link as GraphLink;
              return REL_COLORS[l.type] ?? "rgba(90, 216, 232, 0.35)";
            }}
            backgroundColor="rgba(0,0,0,0)"
            onNodeClick={(node) => {
              const n = node as GraphNode;
              if (isPersonLikeLabel(n.group)) {
                setFocusedPersonId(n.id);
                void onExpand(n);
              }
            }}
          />
        )}
      </div>
    </PanelCard>
  );
}
