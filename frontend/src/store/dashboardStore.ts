import { create } from "zustand";

export type YearRange = readonly [number, number];

export interface DashboardState {
  yearRange: YearRange;
  selectedGenres: string[];
  focusedPersonId: string | null;
  comparePersonIds: string[];
  focusedTimeRange: YearRange | null;
  highlightSongIds: string[];
  setYearRange: (range: YearRange) => void;
  setSelectedGenres: (genres: string[]) => void;
  setFocusedPersonId: (id: string | null) => void;
  clearFocus: () => void;
  setComparePersonIds: (ids: string[]) => void;
  toggleComparePerson: (id: string) => void;
  setFocusedTimeRange: (range: YearRange | null) => void;
  setHighlightSongIds: (ids: string[]) => void;
  /** 与后端查询参数对齐的稳定序列化，供 React Query key 使用 */
  queryFingerprint: () => Record<string, string | number | boolean | null>;
}

const DEFAULT_YEAR_RANGE: YearRange = [2023, 2040] as const;

export const useDashboardStore = create<DashboardState>((set, get) => ({
  yearRange: DEFAULT_YEAR_RANGE,
  selectedGenres: [],
  focusedPersonId: null,
  comparePersonIds: [],
  focusedTimeRange: null,
  highlightSongIds: [],

  setYearRange: (yearRange) => set({ yearRange }),
  setSelectedGenres: (selectedGenres) => set({ selectedGenres }),
  setFocusedPersonId: (focusedPersonId) => set({ focusedPersonId }),
  clearFocus: () =>
    set({
      focusedPersonId: null,
      focusedTimeRange: null,
      highlightSongIds: [],
    }),
  setComparePersonIds: (comparePersonIds) => set({ comparePersonIds }),
  toggleComparePerson: (id) =>
    set((s) => {
      const has = s.comparePersonIds.includes(id);
      const next = has
        ? s.comparePersonIds.filter((x) => x !== id)
        : s.comparePersonIds.length >= 3
          ? [...s.comparePersonIds.slice(1), id]
          : [...s.comparePersonIds, id];
      return { comparePersonIds: next };
    }),
  setFocusedTimeRange: (focusedTimeRange) => set({ focusedTimeRange }),
  setHighlightSongIds: (highlightSongIds) => set({ highlightSongIds }),

  queryFingerprint: () => {
    const s = get();
    const [ys, ye] = s.yearRange;
    const [fts, fte] = s.focusedTimeRange ?? [null, null];
    return {
      start_year: ys,
      end_year: ye,
      genres: s.selectedGenres.join("|") || "__all__",
      focused_person: s.focusedPersonId,
      focus_start: fts,
      focus_end: fte,
      compare: s.comparePersonIds.join("|") || "__none__",
    };
  },
}));
