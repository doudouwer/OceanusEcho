import ReactECharts from "echarts-for-react";
import { useMemo } from "react";
import { useDashboardStore } from "@/store/dashboardStore";
import { PanelCard } from "@/components/panels/PanelCard";
import styles from "./StarProfilerPanel.module.css";

const DEMO_IDS = ["demo-sailor", "demo-a", "demo-b"] as const;

export function StarProfilerPanel() {
  const comparePersonIds = useDashboardStore((s) => s.comparePersonIds);
  const toggleComparePerson = useDashboardStore((s) => s.toggleComparePerson);
  const yearRange = useDashboardStore((s) => s.yearRange);

  const activeIds = comparePersonIds.length > 0 ? comparePersonIds : [...DEMO_IDS];

  const option = useMemo(() => {
    const indicators = [
      { name: "作品数", max: 100 },
      { name: "Notable 率", max: 1 },
      { name: "合作者", max: 40 },
      { name: "流派广度", max: 10 },
      { name: "图度数", max: 50 },
    ];

    const seriesData = activeIds.map((id, idx) => {
      const seed = id.split("").reduce((a, c) => a + c.charCodeAt(0), 0);
      const base = (seed % 7) + idx;
      return {
        value: [
          35 + (base * 7) % 55,
          0.15 + (base % 5) * 0.12,
          10 + (base * 3) % 25,
          3 + (base % 6),
          12 + (base * 2) % 30,
        ],
        name: id,
      };
    });

    return {
      backgroundColor: "transparent",
      textStyle: { color: "#e6f2f5" },
      tooltip: { trigger: "item" },
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
        name: { textStyle: { color: "#7a9aa8", fontSize: 11 } },
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
  }, [activeIds]);

  return (
    <PanelCard
      title="艺人画像"
      tag="Star Profiler"
      description="雷达对比 + 指标矩阵占位。接 GET /analysis/person-profile；comparePersonIds 最多 3 人。"
    >
      <div className={styles.toolbar}>
        <span className={styles.toolbarHint}>演示对比人（点击切换，最多 3 人）：</span>
        <div className={styles.chips}>
          {DEMO_IDS.map((id) => {
            const on = comparePersonIds.length === 0 ? true : comparePersonIds.includes(id);
            return (
              <button
                key={id}
                type="button"
                className={on ? styles.chipOn : styles.chip}
                onClick={() => toggleComparePerson(id)}
              >
                {id}
              </button>
            );
          })}
        </div>
        <span className={styles.toolbarHint}>
          年窗 {yearRange[0]}–{yearRange[1]}
        </span>
      </div>
      <ReactECharts style={{ height: "100%", minHeight: 260 }} option={option} notMerge />
    </PanelCard>
  );
}
