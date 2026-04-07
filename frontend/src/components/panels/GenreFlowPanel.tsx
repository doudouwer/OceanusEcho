import ReactECharts from "echarts-for-react";
import { useMemo } from "react";
import { useDashboardStore } from "@/store/dashboardStore";
import { PanelCard } from "@/components/panels/PanelCard";

export function GenreFlowPanel() {
  const yearRange = useDashboardStore((s) => s.yearRange);
  const selectedGenres = useDashboardStore((s) => s.selectedGenres);

  const option = useMemo(
    () => ({
      backgroundColor: "transparent",
      textStyle: { color: "#e6f2f5" },
      tooltip: { trigger: "item", triggerOn: "mousemove" },
      series: [
        {
          type: "sankey",
          emphasis: { focus: "adjacency" },
          layoutIterations: 32,
          data: [
            { name: "Oceanus Folk" },
            { name: "Indie Pop" },
            { name: "Indie Folk" },
            { name: "Darkwave" },
          ],
          links: [
            { source: "Oceanus Folk", target: "Indie Pop", value: 42 },
            { source: "Oceanus Folk", target: "Indie Folk", value: 28 },
            { source: "Indie Folk", target: "Indie Pop", value: 15 },
            { source: "Darkwave", target: "Indie Pop", value: 8 },
          ],
          lineStyle: { color: "gradient", curveness: 0.5, opacity: 0.45 },
          label: { color: "#e6f2f5" },
        },
      ],
    }),
    [],
  );

  const filterHint =
    selectedGenres.length > 0 ? `已选流派：${selectedGenres.join("、")}` : "未选流派筛选（展示全部分流演示）";

  return (
    <PanelCard
      title="流派演变"
      tag="Genre Flow"
      description="桑基/河流图占位。接 GET /analysis/genre-flow，参数与 yearRange、genres 对齐。"
    >
      <p style={{ margin: "0 0.5rem", fontSize: "0.75rem", color: "var(--text-muted)" }}>
        {filterHint} · 年窗 {yearRange[0]}–{yearRange[1]}
      </p>
      <ReactECharts style={{ height: "100%", minHeight: 240 }} option={option} notMerge />
    </PanelCard>
  );
}
