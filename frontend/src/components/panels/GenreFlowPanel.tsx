import { useQuery } from "@tanstack/react-query";
import ReactECharts from "echarts-for-react";
import { useMemo, useState } from "react";
import { fetchGenreFlow, type GenreFlowPayload } from "@/api/oceanus";
import { useDashboardStore } from "@/store/dashboardStore";
import { PanelCard } from "@/components/panels/PanelCard";
import panelStyles from "@/components/panels/PanelCard.module.css";

type Metric = "style_edges" | "genre_mix";

function normalizeBrushRange(rawRange: unknown, years: number[]): readonly [number, number] | null {
  if (!Array.isArray(rawRange) || rawRange.length < 2 || years.length === 0) return null;
  const [rawA, rawB] = rawRange;
  const minYear = years[0];
  const maxYear = years[years.length - 1];

  const toYear = (value: unknown) => {
    const num = typeof value === "number" ? value : Number(value);
    if (!Number.isFinite(num)) return null;
    if (Number.isInteger(num) && num >= 0 && num < years.length) return years[num];
    return Math.max(minYear, Math.min(maxYear, Math.round(num)));
  };

  const y1 = toYear(rawA);
  const y2 = toYear(rawB);
  if (y1 == null || y2 == null) return null;
  return y1 <= y2 ? [y1, y2] : [y2, y1];
}

function filterGenrePayload(payload: GenreFlowPayload, selectedGenres: string[], metric: Metric): GenreFlowPayload {
  if (!selectedGenres.length) return payload;
  if (metric === "genre_mix") {
    return {
      series: (payload.series ?? []).filter((seriesRow) => selectedGenres.includes(seriesRow.genre)),
    };
  }

  const allowed = new Set(selectedGenres);
  const links = (payload.links ?? []).filter(
    (link) => allowed.has(link.source) || allowed.has(link.target),
  );
  const nodeIds = new Set<string>();
  links.forEach((link) => {
    nodeIds.add(link.source);
    nodeIds.add(link.target);
  });
  return {
    nodes: (payload.nodes ?? []).filter((node) => nodeIds.has(node.id)),
    links,
  };
}

export function GenreFlowPanel() {
  const yearRange = useDashboardStore((s) => s.yearRange);
  const selectedGenres = useDashboardStore((s) => s.selectedGenres);
  const focusedTimeRange = useDashboardStore((s) => s.focusedTimeRange);
  const setFocusedTimeRange = useDashboardStore((s) => s.setFocusedTimeRange);
  const [metric, setMetric] = useState<Metric>("genre_mix");

  const sourceGenre = selectedGenres.length === 1 ? selectedGenres[0] : undefined;

  const { data, isPending, isError, error } = useQuery({
    queryKey: ["genre-flow", yearRange[0], yearRange[1], metric, sourceGenre ?? "", selectedGenres.join("|")],
    queryFn: () =>
      fetchGenreFlow({
        start_year: yearRange[0],
        end_year: yearRange[1],
        metric,
        source_genre: sourceGenre,
        limit: 100,
      }),
  });

  const filteredData = useMemo(
    () => (data ? filterGenrePayload(data, selectedGenres, metric) : null),
    [data, metric, selectedGenres],
  );

  const option = useMemo(() => {
    if (!filteredData) return null;

    if (metric === "style_edges" && filteredData.nodes?.length && filteredData.links?.length) {
      const nodes = filteredData.nodes.map((n) => ({ name: n.id }));
      const links = filteredData.links.map((l) => ({
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
            data: nodes,
            links,
            lineStyle: { color: "gradient", curveness: 0.5, opacity: 0.45 },
            label: { color: "#e6f2f5" },
          },
        ],
      };
    }

    if (metric === "genre_mix" && filteredData.series?.length) {
      const sumGenre = (seriesRow: (typeof filteredData.series)[0]) =>
        seriesRow.points.reduce((acc, point) => acc + point.value, 0);
      const top = [...filteredData.series].sort((a, b) => sumGenre(b) - sumGenre(a)).slice(0, 14);
      const years = new Set<number>();
      top.forEach((seriesRow) => seriesRow.points.forEach((point) => years.add(point.year)));
      const yearArr = [...years].sort((a, b) => a - b);
      if (yearArr.length === 0) return null;
      const series = top.map((genreRow, index) => ({
        name: genreRow.genre,
        type: "line" as const,
        stack: "total",
        areaStyle: {},
        smooth: true,
        emphasis: { focus: "series" },
        lineStyle: { width: 1.4 },
        color: index === 0 && genreRow.genre === "Oceanus Folk" ? "#5ad8e8" : undefined,
        data: yearArr.map((year) => {
          const point = genreRow.points.find((item) => item.year === year);
          return point ? point.value : 0;
        }),
      }));
      return {
        backgroundColor: "transparent",
        animation: false,
        textStyle: { color: "#e6f2f5" },
        tooltip: { trigger: "axis" },
        brush: {
          toolbox: ["lineX", "clear"],
          xAxisIndex: 0,
          brushMode: "single",
          throttleType: "debounce",
          throttleDelay: 250,
          brushStyle: {
            borderWidth: 1,
            color: "rgba(90, 216, 232, 0.12)",
            borderColor: "rgba(90, 216, 232, 0.8)",
          },
        },
        legend: {
          type: "scroll",
          bottom: 0,
          textStyle: { color: "#7a9aa8", fontSize: 10 },
        },
        grid: { left: 48, right: 16, top: 24, bottom: 72 },
        xAxis: { type: "category", data: yearArr, axisLabel: { color: "#7a9aa8" } },
        yAxis: {
          type: "value",
          axisLabel: { color: "#7a9aa8" },
          splitLine: { lineStyle: { color: "#1e3544" } },
        },
        series,
      };
    }

    return null;
  }, [filteredData, metric]);

  const brushYears = useMemo(() => {
    const series = filteredData?.series ?? [];
    const years = new Set<number>();
    series.forEach((row) => row.points.forEach((point) => years.add(point.year)));
    return [...years].sort((a, b) => a - b);
  }, [filteredData]);

  const onEvents = useMemo(
    () => ({
      brushEnd: (params: { areas?: Array<{ coordRange?: unknown }> }) => {
        const normalized = normalizeBrushRange(params?.areas?.[0]?.coordRange, brushYears);
        setFocusedTimeRange(normalized);
      },
    }),
    [brushYears, setFocusedTimeRange],
  );

  const filterHint =
    selectedGenres.length > 1
      ? `Filtered to ${selectedGenres.join(" + ")}`
      : selectedGenres.length === 1
        ? `Source genre: ${selectedGenres[0]}`
        : "No genre filter is active.";

  return (
    <PanelCard
      title="Genre evolution"
      tag="Genre Flow"
      description="GET /api/v1/analysis/genre-flow / River for temporal diffusion and Sankey for style-edge mixing."
    >
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center", margin: "0 0.5rem 0.35rem" }}>
        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
          {filterHint} / {yearRange[0]}-{yearRange[1]}
        </span>
        <div style={{ display: "flex", gap: 4 }}>
          <button
            type="button"
            className={metric === "style_edges" ? panelStyles.tagBtnOn : panelStyles.tagBtn}
            onClick={() => setMetric("style_edges")}
          >
            Sankey
          </button>
          <button
            type="button"
            className={metric === "genre_mix" ? panelStyles.tagBtnOn : panelStyles.tagBtn}
            onClick={() => setMetric("genre_mix")}
          >
            River
          </button>
        </div>
        {focusedTimeRange && (
          <button type="button" className={panelStyles.tagBtn} onClick={() => setFocusedTimeRange(null)}>
            Clear linked range {focusedTimeRange[0]}-{focusedTimeRange[1]}
          </button>
        )}
      </div>
      {metric === "genre_mix" && (
        <p style={{ margin: "0 0.5rem 0.35rem", fontSize: "0.72rem", color: "var(--text-muted)" }}>
          Brush the fusion years in the river chart to update Influence Galaxy.
        </p>
      )}
      {isPending && <div className={panelStyles.empty}>Loading...</div>}
      {isError && (
        <div className={panelStyles.empty}>
          Failed to load: {error instanceof Error ? error.message : "Unknown error"}
          <br />
          <small>Ensure the backend is running and Neo4j has data loaded.</small>
        </div>
      )}
      {!isPending && !isError && !option && (
        <div className={panelStyles.empty}>No genre data in this window. Try other years or genres.</div>
      )}
      {!isPending && !isError && option && (
        <ReactECharts
          style={{ height: "100%", minHeight: 240 }}
          option={option}
          notMerge
          onEvents={metric === "genre_mix" ? onEvents : undefined}
        />
      )}
    </PanelCard>
  );
}
