import { useQuery } from "@tanstack/react-query";
import ReactECharts from "echarts-for-react";
import { useMemo } from "react";
import { fetchPersonProfileNormalized, type NormalizedProfile } from "@/api/oceanus";
import { useDashboardStore } from "@/store/dashboardStore";
import { PanelCard } from "@/components/panels/PanelCard";
import panelStyles from "@/components/panels/PanelCard.module.css";
import styles from "./StarProfilerPanel.module.css";

const DIM_LABELS: Record<string, string> = {
  song_count: "作品数",
  notable_rate: "Notable 率",
  active_years: "活跃年数",
  unique_collaborators: "合作者",
  genre_entropy: "流派熵",
  degree: "度数",
  pagerank: "PageRank",
};

type RadarDatum = { value: number[]; name: string; raw: NormalizedProfile };

export function StarProfilerPanel() {
  const comparePersonIds = useDashboardStore((s) => s.comparePersonIds);
  const toggleComparePerson = useDashboardStore((s) => s.toggleComparePerson);
  const focusedPersonId = useDashboardStore((s) => s.focusedPersonId);
  const yearRange = useDashboardStore((s) => s.yearRange);

  const ids = useMemo(() => {
    if (comparePersonIds.length > 0) return comparePersonIds.slice(0, 3);
    if (focusedPersonId) return [focusedPersonId];
    return [];
  }, [comparePersonIds, focusedPersonId]);

  const { data, isPending, isError, error } = useQuery({
    queryKey: ["person-profile", ids.join(","), yearRange[0], yearRange[1]],
    queryFn: () => fetchPersonProfileNormalized(ids, yearRange[0], yearRange[1]),
    enabled: ids.length >= 1,
  });

  const option = useMemo(() => {
    if (!data?.profiles?.length || !data.dimensions?.length) return null;

    const dimensions = data.dimensions;
    const indicators = dimensions.map((d) => ({
      name: DIM_LABELS[d] ?? d,
      max: 1,
      min: 0,
    }));

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
        formatter: (p: { data?: RadarDatum }) => {
          const prof = p.data?.raw;
          if (!prof) return "";
          const lines = dimensions.map(
            (d) => `${DIM_LABELS[d] ?? d}: ${prof.raw_metrics?.[d] ?? prof.metrics[d] ?? "-"}`,
          );
          return [`<b>${prof.name}</b>`, ...lines].join("<br/>");
        },
      },
      legend: {
        data: seriesData.map((d) => d.name),
        textStyle: { color: "#7a9aa8" },
        bottom: 0,
      },
      radar: {
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
      title="艺人画像"
      tag="Star Profiler"
      description="GET /api/v1/analysis/person-profile?normalized=true。对比区最多 3 人；未选对比时用当前聚焦艺人。"
    >
      <div className={styles.toolbar}>
        <span className={styles.toolbarHint}>对比列表（点击移除）：</span>
        <div className={styles.chips}>
          {comparePersonIds.length === 0 ? (
            <span className={styles.toolbarHint}>
              空 — 点顶部 Ivy Echoes 成员加入对比；或展开「搜索其他艺人」。
            </span>
          ) : (
            comparePersonIds.map((id) => (
              <button key={id} type="button" className={styles.chipOn} onClick={() => toggleComparePerson(id)}>
                {id} ✕
              </button>
            ))
          )}
        </div>
        <span className={styles.toolbarHint}>
          年窗 {yearRange[0]}–{yearRange[1]}
        </span>
      </div>
      {ids.length === 0 && (
        <div className={panelStyles.empty}>
          未选择主角。顶部应默认 Sailor Shift；若清空过 id，请点「恢复 Sailor 视角」或手动输入 original_id。
        </div>
      )}
      {ids.length >= 1 && isPending && <div className={panelStyles.empty}>加载中…</div>}
      {ids.length >= 1 && isError && (
        <div className={panelStyles.empty}>
          加载失败：{error instanceof Error ? error.message : "未知错误"}
        </div>
      )}
      {ids.length >= 1 && !isPending && !isError && !option && (
        <div className={panelStyles.empty}>未返回画像数据。</div>
      )}
      {ids.length >= 1 && !isPending && !isError && option && (
        <ReactECharts style={{ height: "100%", minHeight: 260 }} option={option} notMerge />
      )}
    </PanelCard>
  );
}
