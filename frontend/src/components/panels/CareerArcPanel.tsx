import { useQuery } from "@tanstack/react-query";
import ReactECharts from "echarts-for-react";
import { useMemo } from "react";
import { fetchCareerTrack, type CareerTrackPayload, type CareerYearAgg } from "@/api/oceanus";
import { useDashboardStore } from "@/store/dashboardStore";
import { PanelCard } from "@/components/panels/PanelCard";
import panelStyles from "@/components/panels/PanelCard.module.css";

const SERIES_COLORS = ["#5ad8e8", "#f0b35f", "#72c68f", "#f58cb8"];

function buildSeriesFromCareer(range: readonly [number, number], byYear: CareerYearAgg[]) {
  const [a, b] = range;
  const years: number[] = [];
  for (let y = a; y <= b; y++) years.push(y);
  const map = new Map(byYear.map((x) => [x.year, x]));
  const song = years.map((y) => map.get(y)?.song_count ?? 0);
  const notable = years.map((y) => map.get(y)?.notable_count ?? 0);
  return { years, song, notable };
}

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

export function CareerArcPanel() {
  const yearRange = useDashboardStore((s) => s.yearRange);
  const focusedPersonId = useDashboardStore((s) => s.focusedPersonId);
  const comparePersonIds = useDashboardStore((s) => s.comparePersonIds);
  const focusedTimeRange = useDashboardStore((s) => s.focusedTimeRange);
  const setFocusedTimeRange = useDashboardStore((s) => s.setFocusedTimeRange);

  const ids = useMemo(() => {
    const ordered = [focusedPersonId, ...comparePersonIds].filter((id): id is string => Boolean(id));
    return [...new Set(ordered)].slice(0, 4);
  }, [comparePersonIds, focusedPersonId]);
  const chartKey = `${ids.join("|")}::${yearRange[0]}-${yearRange[1]}::${focusedTimeRange?.join("-") ?? "all"}`;

  const { data, isPending, isError, error } = useQuery({
    queryKey: ["career-track", ids.join(","), yearRange[0], yearRange[1]],
    queryFn: async () => {
      const settled = await Promise.allSettled(
        ids.map((id) =>
          fetchCareerTrack({
            person_id: id,
            start_year: yearRange[0],
            end_year: yearRange[1],
          }),
        ),
      );
      const successes = settled
        .filter((item): item is PromiseFulfilledResult<CareerTrackPayload> => item.status === "fulfilled")
        .map((item) => item.value);
      if (successes.length === 0) {
        throw new Error("No career timelines returned for the selected artists.");
      }
      return successes;
    },
    enabled: ids.length >= 1,
  });

  const option = useMemo(() => {
    if (!data?.length) return null;
    const years = Array.from(
      { length: yearRange[1] - yearRange[0] + 1 },
      (_, index) => yearRange[0] + index,
    );

    const series = data.flatMap((personData, index) => {
      const color = SERIES_COLORS[index % SERIES_COLORS.length];
      const { song, notable } = buildSeriesFromCareer(yearRange, personData.by_year);
      return [
        {
          name: `${personData.person.name} songs`,
          type: "line",
          smooth: true,
          symbol: "circle",
          emphasis: { focus: "series" },
          areaStyle: index === 0 ? { color: "rgba(90, 216, 232, 0.08)" } : undefined,
          lineStyle: { color, width: index === 0 ? 2.8 : 2 },
          itemStyle: { color },
          data: song,
        },
        {
          name: `${personData.person.name} notable`,
          type: "line",
          smooth: true,
          symbol: "circle",
          symbolSize: 7,
          emphasis: { focus: "series" },
          lineStyle: {
            color,
            width: 1.8,
            type: "dashed",
            opacity: 0.95,
          },
          itemStyle: {
            color,
            borderColor: "#f7fbfc",
            borderWidth: 1,
          },
          data: notable,
        },
      ];
    });

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
        data: series.map((item) => item.name),
        textStyle: { color: "#7a9aa8", fontSize: 10 },
        top: 0,
      },
      grid: { left: 48, right: 16, top: 48, bottom: 56 },
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
      series,
    };
  }, [data, yearRange]);

  const onEvents = useMemo(
    () => ({
      brushEnd: (params: { areas?: Array<{ coordRange?: unknown }> }) => {
        const years = Array.from(
          { length: yearRange[1] - yearRange[0] + 1 },
          (_, index) => yearRange[0] + index,
        );
        const normalized = normalizeBrushRange(params?.areas?.[0]?.coordRange, years);
        setFocusedTimeRange(normalized);
      },
    }),
    [setFocusedTimeRange, yearRange],
  );

  const hint = ids.length === 0
    ? "Search and pick a lead artist to load the career timeline."
    : isPending
      ? "Loading /analysis/career-track..."
      : isError
        ? (error instanceof Error ? error.message : "Failed to load")
        : data
          ? `${data.map((item) => item.person.name).join(" / ")}`
          : "";

  const activeBrushLabel = focusedTimeRange ? `Brush linked years: ${focusedTimeRange[0]}-${focusedTimeRange[1]}` : "Brush a year span to refocus the network.";

  return (
    <PanelCard
      title="Career timeline"
      tag="Career Arc"
      description="GET /api/v1/analysis/career-track: overlay career arcs for the lead plus compare artists, with brush-linked year focus."
    >
      {focusedTimeRange && (
        <div style={{ display: "flex", justifyContent: "space-between", gap: "0.5rem", margin: "0 0.5rem 0.25rem" }}>
          <p style={{ margin: 0, fontSize: "0.75rem", color: "var(--text-muted)" }}>{activeBrushLabel}</p>
          <button type="button" className={panelStyles.tagBtn} onClick={() => setFocusedTimeRange(null)}>
            Clear brush
          </button>
        </div>
      )}
      {!focusedTimeRange && (
        <p style={{ margin: "0 0.5rem 0.25rem", fontSize: "0.75rem", color: "var(--text-muted)" }}>{activeBrushLabel}</p>
      )}
      {ids.length === 0 ? (
        <div className={panelStyles.empty}>{hint}</div>
      ) : isError ? (
        <div className={panelStyles.empty}>{hint}</div>
      ) : isPending || !option ? (
        <div className={panelStyles.empty}>{hint}</div>
      ) : (
        <>
          <p style={{ margin: "0 0.5rem", fontSize: "0.75rem", color: "var(--text-muted)" }}>{hint}</p>
          <ReactECharts
            key={chartKey}
            className={panelStyles.chart}
            style={{ height: "100%" }}
            option={option}
            notMerge
            onEvents={onEvents}
          />
        </>
      )}
    </PanelCard>
  );
}
