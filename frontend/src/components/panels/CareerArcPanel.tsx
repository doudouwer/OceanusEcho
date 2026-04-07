import ReactECharts from "echarts-for-react";
import { useMemo } from "react";
import { DEMO_MODE } from "@/config";
import { useDashboardStore } from "@/store/dashboardStore";
import { PanelCard } from "@/components/panels/PanelCard";
import panelStyles from "@/components/panels/PanelCard.module.css";

function buildDemoSeries(start: number, end: number) {
  const years: number[] = [];
  for (let y = start; y <= end; y++) years.push(y);
  const song = years.map((y) => Math.max(0, Math.round(3 + Math.sin(y / 3) * 2 + (y > 2028 ? 4 : 0))));
  const notable = years.map((_, i) => Math.min(song[i], Math.round(song[i] * (0.2 + (i % 5) * 0.05))));
  return { years, song, notable };
}

export function CareerArcPanel() {
  const yearRange = useDashboardStore((s) => s.yearRange);
  const focusedPersonId = useDashboardStore((s) => s.focusedPersonId);

  const option = useMemo(() => {
    const [a, b] = yearRange;
    const { years, song, notable } = buildDemoSeries(a, b);

    return {
      backgroundColor: "transparent",
      textStyle: { color: "#e6f2f5" },
      tooltip: { trigger: "axis" },
      legend: {
        data: ["作品数", "Notable"],
        textStyle: { color: "#7a9aa8" },
        top: 0,
      },
      grid: { left: 48, right: 16, top: 36, bottom: 56 },
      dataZoom: [
        { type: "inside", xAxisIndex: 0 },
        { type: "slider", xAxisIndex: 0, height: 18, bottom: 8, borderColor: "#1e3544" },
      ],
      xAxis: {
        type: "category",
        data: years,
        axisLabel: { color: "#7a9aa8" },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: "#7a9aa8" },
        splitLine: { lineStyle: { color: "#1e3544" } },
      },
      series: [
        {
          name: "作品数",
          type: "line",
          smooth: true,
          areaStyle: { color: "rgba(90, 216, 232, 0.12)" },
          lineStyle: { color: "#5ad8e8" },
          data: song,
        },
        {
          name: "Notable",
          type: "line",
          smooth: true,
          lineStyle: { color: "#f07178" },
          data: notable,
        },
      ],
    };
  }, [yearRange]);

  const hint =
    !focusedPersonId && !DEMO_MODE
      ? "请在顶部设置聚焦艺人以加载 /analysis/career-track"
      : DEMO_MODE
        ? "演示数据 · 接好 API 后关闭 VITE_DEMO_MODE"
        : `person_id=${focusedPersonId}`;

  return (
    <PanelCard
      title="职业时轴"
      tag="Career Arc"
      description="发片频率、Notable 走势。后续可接 brush/dataZoom 事件写入 focusedTimeRange 联动 Galaxy。"
    >
      {!focusedPersonId && !DEMO_MODE ? (
        <div className={panelStyles.empty}>{hint}</div>
      ) : (
        <>
          <p style={{ margin: "0 0.5rem", fontSize: "0.75rem", color: "var(--text-muted)" }}>{hint}</p>
          <ReactECharts className={panelStyles.chart} style={{ height: "100%" }} option={option} notMerge />
        </>
      )}
    </PanelCard>
  );
}
