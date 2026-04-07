import ForceGraph2D from "react-force-graph-2d";
import { useCallback, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useDashboardStore } from "@/store/dashboardStore";
import { PanelCard } from "@/components/panels/PanelCard";
import panelStyles from "@/components/panels/PanelCard.module.css";

type GraphNode = { id: string; name: string; group: string };
type GraphLink = { source: string; target: string };

const DEMO_GRAPH: { nodes: GraphNode[]; links: GraphLink[] } = {
  nodes: [
    { id: "demo-sailor", name: "Sailor Shift", group: "Person" },
    { id: "demo-a", name: "Collaborator A", group: "Person" },
    { id: "demo-b", name: "Collaborator B", group: "Person" },
    { id: "demo-song-1", name: "Breaking These Chains", group: "Song" },
    { id: "demo-song-2", name: "Unshackled Heart", group: "Song" },
  ],
  links: [
    { source: "demo-sailor", target: "demo-song-1" },
    { source: "demo-a", target: "demo-song-1" },
    { source: "demo-sailor", target: "demo-song-2" },
    { source: "demo-b", target: "demo-song-2" },
    { source: "demo-a", target: "demo-b" },
  ],
};

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

  const data = useMemo(() => DEMO_GRAPH, []);

  const paintNode = useCallback(
    (node: object, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const n = node as GraphNode & { x?: number; y?: number };
      if (n.x == null || n.y == null) return;
      const label = n.name;
      const isFocus = focusedPersonId != null && n.id === focusedPersonId;
      const r = (n.group === "Song" ? 4 : 7) / globalScale;
      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, 2 * Math.PI, false);
      ctx.fillStyle = n.group === "Song" ? "#7a9aa8" : isFocus ? "#5ad8e8" : "#3a7d8c";
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
      ? `细时间窗：${focusedTimeRange[0]}–${focusedTimeRange[1]}（可与 subgraph 参数对齐）`
      : `全局年窗：${yearRange[0]}–${yearRange[1]}`;

  return (
    <PanelCard
      title="影响力网络"
      tag="Influence Galaxy"
      description="力导向子图 + 邻居展开。点击 Person 节点写入 focusedPersonId；接 POST /graph/subgraph 与 GET /graph/expand。"
    >
      <p style={{ margin: "0 0.5rem", fontSize: "0.75rem", color: "var(--text-muted)" }}>{subtitle}</p>
      <div ref={wrapRef} className={panelStyles.chart} style={{ minHeight: 280 }}>
        <ForceGraph2D
          graphData={data}
          width={size.w}
          height={size.h}
          nodeLabel="name"
          nodeCanvasObject={paintNode}
          nodePointerAreaPaint={(node, color, ctx, globalScale) => {
            const n = node as GraphNode & { x?: number; y?: number };
            if (n.x == null || n.y == null) return;
            const r = (n.group === "Song" ? 6 : 10) / globalScale;
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(n.x, n.y, r, 0, 2 * Math.PI, false);
            ctx.fill();
          }}
          linkColor={() => "rgba(90, 216, 232, 0.35)"}
          backgroundColor="rgba(0,0,0,0)"
          onNodeClick={(node) => {
            const n = node as GraphNode;
            if (n.group === "Person") setFocusedPersonId(n.id);
          }}
        />
      </div>
    </PanelCard>
  );
}
