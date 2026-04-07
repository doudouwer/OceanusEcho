import { useDashboardStore } from "@/store/dashboardStore";
import styles from "./GlobalChrome.module.css";

const GENRE_PRESETS = ["Oceanus Folk", "Indie Pop", "Indie Folk", "Darkwave", "Lo-Fi Electronica"];

export function GlobalChrome() {
  const yearRange = useDashboardStore((s) => s.yearRange);
  const setYearRange = useDashboardStore((s) => s.setYearRange);
  const selectedGenres = useDashboardStore((s) => s.selectedGenres);
  const setSelectedGenres = useDashboardStore((s) => s.setSelectedGenres);
  const focusedPersonId = useDashboardStore((s) => s.focusedPersonId);
  const setFocusedPersonId = useDashboardStore((s) => s.setFocusedPersonId);
  const clearFocus = useDashboardStore((s) => s.clearFocus);

  return (
    <div className={styles.chrome}>
      <label className={styles.field}>
        时间范围（年）
        <div className={styles.fieldRow}>
          <input
            className={styles.input}
            type="number"
            value={yearRange[0]}
            min={1980}
            max={2100}
            onChange={(e) => {
              const v = Number(e.target.value);
              setYearRange([Math.min(v, yearRange[1]), yearRange[1]]);
            }}
          />
          <span style={{ color: "var(--text-muted)" }}>—</span>
          <input
            className={styles.input}
            type="number"
            value={yearRange[1]}
            min={1980}
            max={2100}
            onChange={(e) => {
              const v = Number(e.target.value);
              setYearRange([yearRange[0], Math.max(v, yearRange[0])]);
            }}
          />
        </div>
      </label>

      <label className={styles.field}>
        流派筛选（多选）
        <select
          className={styles.select}
          multiple
          size={3}
          value={selectedGenres}
          onChange={(e) => {
            const next = Array.from(e.target.selectedOptions).map((o) => o.value);
            setSelectedGenres(next);
          }}
        >
          {GENRE_PRESETS.map((g) => (
            <option key={g} value={g}>
              {g}
            </option>
          ))}
        </select>
      </label>

      <div className={styles.field} style={{ flex: "1 1 200px" }}>
        聚焦艺人（演示：输入任意 id）
        <div className={styles.searchRow}>
          <input
            className={styles.input}
            placeholder="person_id"
            value={focusedPersonId ?? ""}
            onChange={(e) => setFocusedPersonId(e.target.value || null)}
          />
          <button type="button" className={styles.btn} onClick={() => clearFocus()}>
            清除
          </button>
        </div>
      </div>

      <div className={styles.field}>
        联动状态
        <div className={styles.pill}>
          当前聚焦：<strong>{focusedPersonId ?? "未选择"}</strong>
        </div>
      </div>
    </div>
  );
}
