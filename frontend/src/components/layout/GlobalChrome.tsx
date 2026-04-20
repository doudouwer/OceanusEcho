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
        <strong>Silas · Oceanus Folk: Then-and-Now</strong> — centered on{" "}
        <strong>{DEFAULT_SAILOR_NAME}</strong> (<code>id {DEFAULT_SAILOR_PERSON_ID}</code>
        ) for profiles and genres; the year window and Ivy Echoes members support comparison.
        {!isSailor && (
          <>
            {" "}
            Current lead id: <strong>{focusedPersonId}</strong>
          </>
        )}
      </div>

      <div className={styles.bandRow}>
        <span className={styles.bandLabel}>Ivy Echoes → compare</span>
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
          Reset to Sailor
        </button>
      </div>

      <div className={styles.chromeRow}>
        <label className={styles.field}>
          Year range
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
          Genres (multi-select)
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
          Lead person id
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
          Status
          <div className={styles.pill}>
            Focus: <strong>{focusedPersonId}</strong>
          </div>
        </div>
      </div>

      <details className={styles.optionalSearch}>
        <summary>Search artists / songs (optional)</summary>
        <div ref={wrapRef} className={styles.searchWrap} style={{ marginTop: "0.5rem" }}>
          <div className={styles.searchRow}>
            <input
              className={styles.input}
              placeholder="Name keyword…"
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
              {isFetching && <div className={styles.dropdownItem}>Searching…</div>}
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
                          Set as lead
                        </button>
                        <button
                          type="button"
                          className={styles.miniBtn}
                          onClick={() => {
                            toggleComparePerson(hit.id);
                            setOpenDropdown(false);
                          }}
                        >
                          Add to compare
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              {!isFetching && searchData?.results?.length === 0 && (
                <div className={styles.dropdownItem}>No results</div>
              )}
            </div>
          )}
        </div>
      </details>
    </div>
  );
}
