import { useQuery } from "@tanstack/react-query";
import ReactECharts from "echarts-for-react";
import { useMemo } from "react";
import { fetchCareerTrack, type CareerYearAgg } from "@/api/oceanus";
import { useDashboardStore } from "@/store/dashboardStore";
import { PanelCard } from "@/components/panels/PanelCard";
import panelStyles from "@/components/panels/PanelCard.module.css";

function buildSeriesFromCareer(range: readonly [number, number], byYear: CareerYearAgg[]) {
  const [a, b] = range;
  const years: number[] = [];
  for (let y = a; y <= b; y++) years.push(y);
  const map = new Map(byYear.map((x) => [x.year, x]));
  const song = years.map((y) => map.get(y)?.song_count ?? 0);
  const notable = years.map((y) => map.get(y)?.notable_count ?? 0);
  return { years, song, notable };
}

export function CareerArcPanel() {
  const yearRange = useDashboardStore((s) => s.yearRange);
  const focusedPersonId = useDashboardStore((s) => s.focusedPersonId);

  const { data, isPending, isError, error } = useQuery({
    queryKey: ["career-track", focusedPersonId ?? "", yearRange[0], yearRange[1]],
    queryFn: () =>
      fetchCareerTrack({
        person_id: focusedPersonId ?? undefined,
        start_year: yearRange[0],
        end_year: yearRange[1],
      }),
    enabled: Boolean(focusedPersonId),
  });

  const option = useMemo(() => {
    if (!data?.by_year) return null;
    const { years, song, notable } = buildSeriesFromCareer(yearRange, data.by_year);
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
  }, [data, yearRange]);

  const hint = !focusedPersonId
    ? "请在顶部搜索并选择聚焦艺人以加载职业时轴"
    : isPending
      ? "正在加载 /analysis/career-track …"
      : isError
        ? (error instanceof Error ? error.message : "加载失败")
        : data
          ? `${data.person.name}（${data.person.id}）· 作品 ${data.summary?.total_works ?? data.works?.length ?? 0} 首`
          : "";

  return (
    <PanelCard
      title="职业时轴"
      tag="Career Arc"
      description="GET /api/v1/analysis/career-track：按年作品数与 Notable 计数；时间范围取仪表盘年窗。"
    >
      {!focusedPersonId ? (
        <div className={panelStyles.empty}>{hint}</div>
      ) : isError ? (
        <div className={panelStyles.empty}>{hint}</div>
      ) : isPending || !option ? (
        <div className={panelStyles.empty}>{hint}</div>
      ) : data.by_year.length === 0 ? (
        <div className={panelStyles.empty}>该时间窗内无作品记录</div>
      ) : (
        <>
          <p style={{ margin: "0 0.5rem", fontSize: "0.75rem", color: "var(--text-muted)" }}>{hint}</p>
          <ReactECharts className={panelStyles.chart} style={{ height: "100%" }} option={option} notMerge />
        </>
      )}
    </PanelCard>
  );
}
