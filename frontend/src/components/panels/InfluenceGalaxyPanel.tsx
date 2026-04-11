import ForceGraph2D from "react-force-graph-2d";
import { useQuery } from "@tanstack/react-query";
import { useCallback, useLayoutEffect, useMemo, useRef, useState } from "react";
import { fetchInfluenceSubgraph, type InfluenceGalaxyPayload } from "@/api/oceanus";
import { useDashboardStore } from "@/store/dashboardStore";
import { PanelCard } from "@/components/panels/PanelCard";
import panelStyles from "@/components/panels/PanelCard.module.css";

type GraphNode = { id: string; name: string; group: string };
type GraphLink = { source: string; target: string };

function payloadToForceGraph(payload: InfluenceGalaxyPayload): { nodes: GraphNode[]; links: GraphLink[] } {
  const nodes = payload.graph.nodes.map((n) => ({
    id: n.id,
    name: (n.name && String(n.name).trim()) || n.id,
    group: n.label,
  }));
  const links = payload.graph.links.map((l) => ({
    source: l.source,
    target: l.target,
  }));
  return { nodes, links };
}

function isSongLikeLabel(label: string) {
  return label === "Song" || label === "Album";
}

function isPersonLikeLabel(label: string) {
  return label === "Person" || label === "MusicalGroup";
}

export function InfluenceGalaxyPanel() {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 640, h: 320 });

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
    ],
    queryFn: () =>
      fetchInfluenceSubgraph({
        start_year: ys,
        end_year: ye,
        genres: selectedGenres,
        seed_person_ids: focusedPersonId ? [focusedPersonId] : [],
        rel_types: [],
        limit_nodes: 500,
        only_notable_songs: false,
      }),
  });

  const graphData = useMemo(() => {
    if (!data?.graph?.nodes?.length) return { nodes: [] as GraphNode[], links: [] as GraphLink[] };
    return payloadToForceGraph(data);
  }, [data]);

  const paintNode = useCallback(
    (node: object, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const n = node as GraphNode & { x?: number; y?: number };
      if (n.x == null || n.y == null) return;
      const label = n.name;
      const isFocus = focusedPersonId != null && n.id === focusedPersonId;
      const r = (isSongLikeLabel(n.group) ? 4 : 7) / globalScale;
      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, 2 * Math.PI, false);
      ctx.fillStyle = isSongLikeLabel(n.group) ? "#7a9aa8" : isFocus ? "#5ad8e8" : "#3a7d8c";
      ctx.fill();
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
      ? `细时间窗：${focusedTimeRange[0]}–${focusedTimeRange[1]} · POST /graph/subgraph`
      : `全局年窗：${yearRange[0]}–${yearRange[1]} · POST /graph/subgraph`;

  const statusLine = isPending
    ? "正在加载子图…"
    : isError
      ? error instanceof Error
        ? error.message
        : "加载失败"
      : `节点 ${graphData.nodes.length} · 边 ${graphData.links.length}`;

  return (
    <PanelCard
      title="影响力网络"
      tag="Influence Galaxy"
      description="力导向子图：种子为当前聚焦艺人（可选）；流派取仪表盘所选。点击 Person / MusicalGroup 切换聚焦。"
    >
      <p style={{ margin: "0 0.5rem", fontSize: "0.75rem", color: "var(--text-muted)" }}>{subtitle}</p>
      <p style={{ margin: "0 0.5rem 0.25rem", fontSize: "0.7rem", color: "var(--text-muted)" }}>{statusLine}</p>
      <div ref={wrapRef} className={panelStyles.chart} style={{ minHeight: 280 }}>
        {isPending ? (
          <div className={panelStyles.empty}>正在加载子图…</div>
        ) : isError ? (
          <div className={panelStyles.empty}>{statusLine}</div>
        ) : graphData.nodes.length === 0 ? (
          <div className={panelStyles.empty}>子图为空，可调整年窗、流派或聚焦艺人后重试</div>
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
            linkColor={() => "rgba(90, 216, 232, 0.35)"}
            backgroundColor="rgba(0,0,0,0)"
            onNodeClick={(node) => {
              const n = node as GraphNode;
              if (isPersonLikeLabel(n.group)) setFocusedPersonId(n.id);
            }}
          />
        )}
      </div>
    </PanelCard>
  );
}
