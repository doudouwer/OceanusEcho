import { create } from "zustand";
import { DEFAULT_SAILOR_PERSON_ID } from "@/config";

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
  /** Stable serialization aligned with backend query params for React Query keys */
  queryFingerprint: () => Record<string, string | number | boolean | null>;
}

const DEFAULT_YEAR_RANGE: YearRange = [2023, 2040] as const;

export const useDashboardStore = create<DashboardState>((set, get) => ({
  yearRange: DEFAULT_YEAR_RANGE,
  /** Default narrative: Oceanus Folk + Sailor */
  selectedGenres: ["Oceanus Folk"],
  focusedPersonId: DEFAULT_SAILOR_PERSON_ID,
  comparePersonIds: [],
  focusedTimeRange: null,
  highlightSongIds: [],

  setYearRange: (yearRange) => set({ yearRange }),
  setSelectedGenres: (selectedGenres) => set({ selectedGenres }),
  setFocusedPersonId: (focusedPersonId) => set({ focusedPersonId }),
  /** Reset to Silas default: Sailor focus, clear compare list and time brush */
  clearFocus: () =>
    set({
      focusedPersonId: DEFAULT_SAILOR_PERSON_ID,
      comparePersonIds: [],
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
