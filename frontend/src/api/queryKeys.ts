import type { DashboardState } from "@/store/dashboardStore";

export const qk = {
  careerTrack: (fp: ReturnType<DashboardState["queryFingerprint"]>, personId: string | null) =>
    ["career-track", fp, personId] as const,
  subgraph: (fp: ReturnType<DashboardState["queryFingerprint"]>) => ["subgraph", fp] as const,
  genreFlow: (fp: ReturnType<DashboardState["queryFingerprint"]>) => ["genre-flow", fp] as const,
  personProfile: (fp: ReturnType<DashboardState["queryFingerprint"]>, ids: string[]) =>
    ["person-profile", fp, ids.join("|")] as const,
  search: (q: string) => ["search", q] as const,
};
