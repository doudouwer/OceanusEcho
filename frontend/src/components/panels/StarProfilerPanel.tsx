import { useQuery } from "@tanstack/react-query";
import ReactECharts from "echarts-for-react";
import { useMemo } from "react";
import { fetchPersonProfileNormalized, type NormalizedProfile } from "@/api/oceanus";
import { useDashboardStore } from "@/store/dashboardStore";
import { PanelCard } from "@/components/panels/PanelCard";
import panelStyles from "@/components/panels/PanelCard.module.css";
import styles from "./StarProfilerPanel.module.css";

const DIM_LABELS: Record<string, string> = {
  song_count: "Song count",
  notable_rate: "Notable rate",
  active_years: "Active years",
  unique_collaborators: "Collaborators",
  genre_entropy: "Genre entropy",
  degree: "Degree",
  pagerank: "PageRank",
};

type RadarDatum = { value: number[]; name: string; raw: NormalizedProfile };

export function StarProfilerPanel() {
  const comparePersonIds = useDashboardStore((s) => s.comparePersonIds);
  const toggleComparePerson = useDashboardStore((s) => s.toggleComparePerson);
  const focusedPersonId = useDashboardStore((s) => s.focusedPersonId);
  const yearRange = useDashboardStore((s) => s.yearRange);

  const ids = useMemo(() => {
    const ordered = [focusedPersonId, ...comparePersonIds].filter((id): id is string => Boolean(id));
    return [...new Set(ordered)].slice(0, 4);
  }, [comparePersonIds, focusedPersonId]);
  const chartKey = `${ids.join("|")}::${yearRange[0]}-${yearRange[1]}`;

  const { data, isPending, isError, error } = useQuery({
    queryKey: ["person-profile", ids.join(","), yearRange[0], yearRange[1]],
    queryFn: () => fetchPersonProfileNormalized(ids, yearRange[0], yearRange[1]),
    enabled: ids.length >= 1,
  });

  const profileNameMap = useMemo(() => {
    const map = new Map<string, string>();
    data?.profiles.forEach((profile) => {
      map.set(profile.person_id, profile.name || profile.person_id);
    });
    return map;
  }, [data]);

  const option = useMemo(() => {
    if (!data?.profiles?.length || !data.dimensions?.length) return null;

    const dimensions = data.dimensions;
    const indicators = dimensions.map((dimension) => {
      const maxValue = Math.max(
        1.2,
        ...data.profiles.map((profile) => Number(profile.metrics[dimension] ?? 0)),
      );
      return {
        name: DIM_LABELS[dimension] ?? dimension,
        max: Math.ceil(maxValue * 10) / 10,
        min: 0,
      };
    });

    const seriesData: RadarDatum[] = data.profiles.map((p) => ({
      name: p.name || p.person_id,
      value: dimensions.map((d) => p.metrics[d] ?? 0),
      raw: p,
    }));

    return {
      backgroundColor: "transparent",
      textStyle: { color: "#e6f2f5" },
      tooltip: {
        trigger: "item",
        formatter: (params: { data?: RadarDatum }) => {
          const profile = params.data?.raw;
          if (!profile) return "";
          const lines = dimensions.map(
            (d) => `${DIM_LABELS[d] ?? d}: ${profile.raw_metrics?.[d] ?? profile.metrics[d] ?? "-"}`,
          );
          return [`<b>${profile.name}</b>`, ...lines].join("<br/>");
        },
      },
      legend: {
        data: seriesData.map((item) => item.name),
        textStyle: { color: "#7a9aa8" },
        bottom: 4,
      },
      radar: {
        center: ["54%", "52%"],
        radius: "58%",
        indicator: indicators,
        splitLine: { lineStyle: { color: "#1e3544" } },
        splitArea: { show: false },
        axisLine: { lineStyle: { color: "#1e3544" } },
        name: { textStyle: { color: "#7a9aa8", fontSize: 10 } },
      },
      series: [
        {
          type: "radar",
          data: seriesData,
          symbolSize: 6,
          lineStyle: { width: 2 },
          areaStyle: { opacity: 0.08 },
        },
      ],
    };
  }, [data]);

  return (
    <PanelCard
      title="Artist profile"
      tag="Star Profiler"
      description="GET /api/v1/analysis/person-profile?normalized=true. The current lead stays as the anchor, with up to three additional artists for comparison."
    >
      <div className={styles.toolbar}>
        <span className={styles.toolbarHint}>Compare list (click to remove):</span>
        <div className={styles.chips}>
          {comparePersonIds.length === 0 ? (
            <span className={styles.toolbarHint}>
              Empty. Add Ivy Echoes members from the header, or search for more artists.
            </span>
          ) : (
            comparePersonIds.map((id) => (
              <button key={id} type="button" className={styles.chipOn} onClick={() => toggleComparePerson(id)}>
                {profileNameMap.get(id) ?? id} x
              </button>
            ))
          )}
        </div>
        <span className={styles.toolbarHint}>
          Anchor: {data?.anchor_name ?? focusedPersonId ?? "none"} / {yearRange[0]}-{yearRange[1]}
        </span>
      </div>
      {ids.length === 0 && (
        <div className={panelStyles.empty}>
          No lead selected. Reset to Sailor Shift or choose an artist from search.
        </div>
      )}
      {ids.length >= 1 && isPending && <div className={panelStyles.empty}>Loading...</div>}
      {ids.length >= 1 && isError && (
        <div className={panelStyles.empty}>
          Failed to load: {error instanceof Error ? error.message : "Unknown error"}
        </div>
      )}
      {ids.length >= 1 && !isPending && !isError && !option && (
        <div className={panelStyles.empty}>No profile data returned.</div>
      )}
      {ids.length >= 1 && !isPending && !isError && option && (
        <ReactECharts key={chartKey} style={{ height: "100%", minHeight: 260 }} option={option} notMerge />
      )}
    </PanelCard>
  );
}
