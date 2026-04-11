import { useQuery } from "@tanstack/react-query";
import ReactECharts from "echarts-for-react";
import { useMemo, useState } from "react";
import { fetchGenreFlow } from "@/api/oceanus";
import { useDashboardStore } from "@/store/dashboardStore";
import { PanelCard } from "@/components/panels/PanelCard";
import panelStyles from "@/components/panels/PanelCard.module.css";

type Metric = "style_edges" | "genre_mix";

export function GenreFlowPanel() {
  const yearRange = useDashboardStore((s) => s.yearRange);
  const selectedGenres = useDashboardStore((s) => s.selectedGenres);
  const [metric, setMetric] = useState<Metric>("style_edges");

  const sourceGenre = selectedGenres.length === 1 ? selectedGenres[0] : undefined;

  const { data, isPending, isError, error } = useQuery({
    queryKey: ["genre-flow", yearRange[0], yearRange[1], metric, sourceGenre ?? ""],
    queryFn: () =>
      fetchGenreFlow({
        start_year: yearRange[0],
        end_year: yearRange[1],
        metric,
        source_genre: sourceGenre,
        limit: 100,
      }),
  });

  const option = useMemo(() => {
    if (!data) return null;

    if (metric === "style_edges" && data.nodes?.length && data.links?.length) {
      const names = data.nodes.map((n) => ({ name: n.name ?? n.id }));
      const links = data.links.map((l) => ({
        source: l.source,
        target: l.target,
        value: l.value,
      }));
      return {
        backgroundColor: "transparent",
        textStyle: { color: "#e6f2f5" },
        tooltip: { trigger: "item", triggerOn: "mousemove" },
        series: [
          {
            type: "sankey",
            emphasis: { focus: "adjacency" },
            layoutIterations: 32,
            data: names,
            links,
            lineStyle: { color: "gradient", curveness: 0.5, opacity: 0.45 },
            label: { color: "#e6f2f5" },
          },
        ],
      };
    }

    if (metric === "genre_mix" && data.series?.length) {
      const sumGenre = (s: (typeof data.series)[0]) =>
        s.points.reduce((a, p) => a + p.value, 0);
      const top = [...data.series].sort((a, b) => sumGenre(b) - sumGenre(a)).slice(0, 14);
      const years = new Set<number>();
      top.forEach((s) => s.points.forEach((p) => years.add(p.year)));
      const yearArr = [...years].sort((a, b) => a - b);
      if (yearArr.length === 0) return null;
      const series = top.map((g) => ({
        name: g.genre,
        type: "line" as const,
        stack: "total",
        areaStyle: {},
        smooth: true,
        data: yearArr.map((y) => {
          const pt = g.points.find((p) => p.year === y);
          return pt ? pt.value : 0;
        }),
      }));
      return {
        backgroundColor: "transparent",
        textStyle: { color: "#e6f2f5" },
        tooltip: { trigger: "axis" },
        legend: {
          type: "scroll",
          bottom: 0,
          textStyle: { color: "#7a9aa8", fontSize: 10 },
        },
        grid: { left: 48, right: 16, top: 24, bottom: 72 },
        xAxis: { type: "category", data: yearArr, axisLabel: { color: "#7a9aa8" } },
        yAxis: { type: "value", axisLabel: { color: "#7a9aa8" }, splitLine: { lineStyle: { color: "#1e3544" } } },
        series,
      };
    }

    return null;
  }, [data, metric]);

  const filterHint =
    selectedGenres.length > 1
      ? "多选流派时桑基不按单流派过滤；仅选 1 个流派时可聚焦 source_genre"
      : selectedGenres.length === 1
        ? `聚焦源流：${selectedGenres[0]}`
        : "未选单一流派：展示时间窗内全部桑基/河流";

  return (
    <PanelCard
      title="流派演变"
      tag="Genre Flow"
      description="GET /api/v1/analysis/genre-flow — style_edges 桑基 · genre_mix 堆叠面积（近似河流）。"
    >
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center", margin: "0 0.5rem 0.35rem" }}>
        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
          {filterHint} · {yearRange[0]}–{yearRange[1]}
        </span>
        <div style={{ display: "flex", gap: 4 }}>
          <button
            type="button"
            className={metric === "style_edges" ? panelStyles.tagBtnOn : panelStyles.tagBtn}
            onClick={() => setMetric("style_edges")}
          >
            桑基
          </button>
          <button
            type="button"
            className={metric === "genre_mix" ? panelStyles.tagBtnOn : panelStyles.tagBtn}
            onClick={() => setMetric("genre_mix")}
          >
            河流
          </button>
        </div>
      </div>
      {isPending && <div className={panelStyles.empty}>加载中…</div>}
      {isError && (
        <div className={panelStyles.empty}>
          加载失败：{error instanceof Error ? error.message : "未知错误"}
          <br />
          <small>请确认后端已启动且 Neo4j 已导入数据。</small>
        </div>
      )}
      {!isPending && !isError && !option && (
        <div className={panelStyles.empty}>该时间窗内暂无流派数据，可调整年份或流派筛选。</div>
      )}
      {!isPending && !isError && option && (
        <ReactECharts style={{ height: "100%", minHeight: 240 }} option={option} notMerge />
      )}
    </PanelCard>
  );
}
