import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { fetchSearch } from "@/api/oceanus";
import {
  DEFAULT_SAILOR_NAME,
  DEFAULT_SAILOR_PERSON_ID,
  IVY_ECHOES_BANDMATES,
} from "@/config";
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
  const toggleComparePerson = useDashboardStore((s) => s.toggleComparePerson);

  const [searchQ, setSearchQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [openDropdown, setOpenDropdown] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedQ(searchQ.trim()), 280);
    return () => window.clearTimeout(t);
  }, [searchQ]);

  const { data: searchData, isFetching } = useQuery({
    queryKey: ["search", debouncedQ],
    queryFn: () => fetchSearch(debouncedQ, "all", 24),
    enabled: debouncedQ.length >= 1,
  });

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setOpenDropdown(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const isSailor = focusedPersonId === DEFAULT_SAILOR_PERSON_ID;

  return (
    <div className={styles.chrome}>
      <div className={styles.narrative}>
        <strong>Silas · Oceanus Folk: Then-and-Now</strong> — 默认围绕{" "}
        <strong>{DEFAULT_SAILOR_NAME}</strong>（<code>id {DEFAULT_SAILOR_PERSON_ID}</code>
        ）展示画像与流派；年窗与「Ivy Echoes」成员可辅助对比。
        {!isSailor && (
          <>
            {" "}
            当前主角 id：<strong>{focusedPersonId}</strong>
          </>
        )}
      </div>

      <div className={styles.bandRow}>
        <span className={styles.bandLabel}>Ivy Echoes → 对比</span>
        {IVY_ECHOES_BANDMATES.map((m) => (
          <button
            key={m.id}
            type="button"
            className={styles.miniBtn}
            title={m.name}
            onClick={() => toggleComparePerson(m.id)}
          >
            {m.name.split(" ")[0]}
          </button>
        ))}
        <button type="button" className={styles.btn} onClick={() => clearFocus()}>
          恢复 Sailor 视角
        </button>
      </div>

      <div className={styles.chromeRow}>
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

        <div className={styles.field}>
          当前主角 id
          <div className={styles.searchRow}>
            <input
              className={styles.input}
              placeholder={DEFAULT_SAILOR_PERSON_ID}
              value={focusedPersonId ?? ""}
              onChange={(e) => setFocusedPersonId(e.target.value || null)}
            />
          </div>
        </div>

        <div className={styles.field}>
          状态
          <div className={styles.pill}>
            聚焦 <strong>{focusedPersonId}</strong>
          </div>
        </div>
      </div>

      <details className={styles.optionalSearch}>
        <summary>搜索其他艺人 / 歌曲（可选）</summary>
        <div ref={wrapRef} className={styles.searchWrap} style={{ marginTop: "0.5rem" }}>
          <div className={styles.searchRow}>
            <input
              className={styles.input}
              placeholder="名称关键词…"
              value={searchQ}
              onChange={(e) => {
                setSearchQ(e.target.value);
                setOpenDropdown(true);
              }}
              onFocus={() => setOpenDropdown(true)}
            />
          </div>
          {openDropdown && debouncedQ.length >= 1 && (
            <div className={styles.dropdown}>
              {isFetching && <div className={styles.dropdownItem}>搜索中…</div>}
              {!isFetching &&
                searchData?.results?.map((hit) => (
                  <div key={`${hit.type}-${hit.id}`} className={styles.dropdownItem}>
                    <div>
                      <strong>{hit.label}</strong>{" "}
                      <span className={styles.dropdownMeta}>
                        {hit.type} · id {hit.id}
                      </span>
                    </div>
                    {hit.subtitle && <div className={styles.dropdownMeta}>{hit.subtitle}</div>}
                    {hit.type === "person" && (
                      <div className={styles.rowBtns}>
                        <button
                          type="button"
                          className={styles.miniBtn}
                          onClick={() => {
                            setFocusedPersonId(hit.id);
                            setOpenDropdown(false);
                          }}
                        >
                          设为主角
                        </button>
                        <button
                          type="button"
                          className={styles.miniBtn}
                          onClick={() => {
                            toggleComparePerson(hit.id);
                            setOpenDropdown(false);
                          }}
                        >
                          加入对比
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              {!isFetching && searchData?.results?.length === 0 && (
                <div className={styles.dropdownItem}>无结果</div>
              )}
            </div>
          )}
        </div>
      </details>
    </div>
  );
}
