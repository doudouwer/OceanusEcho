export type PanelKey = "career" | "galaxy" | "genre" | "profiler";

export type Act = {
  id: number;
  kicker: string;
  title: string;
  subtitle: string;
  objective?: string;
  voiceover: string;
  activePanels: PanelKey[];
  insight: string;
};

export const acts: Act[] = [
  {
    id: 1,
    kicker: "Act I — Rise of a Star",
    title: "Profile Sailor Shift",
    subtitle: "The Career Arc and Influence Galaxy together reveal how a career builds — and breaks.",
    objective: "",
    voiceover:
      "For years, output stayed modest. Then 2028 arrived: song count peaked and Notable tags surged in lockstep — a visible inflection point. That is not luck. It is a signal.",
    activePanels: ["career", "galaxy"],
    insight: "Her career reads like a coiled spring: steady pressure builds, then releases all at once.",
  },
  {
    id: 2,
    kicker: "Act II — Genre Diffusion",
    title: "Map Oceanus Folk",
    subtitle: "Three views reveal how a genre spreads — and who carries it across boundaries.",
    objective: "",
    voiceover:
      "The growth curve tells a clear story: Oceanus Folk stayed dormant before 2022, then exploded upward in a single year. That is explosive diffusion — but the true amplifier is not a single artist. It is a network of bridge collaborators who introduced Oceanus Folk's sound to neighboring genres.",
    activePanels: ["genre", "galaxy"],
    insight: "The breakout was not a solo broadcast — it was a relay. Bridge artists carried the signal across genre lines.",
  },
  {
    id: 3,
    kicker: "Act III — Tomorrow's Stars",
    title: "Predict Rising Stars",
    subtitle: "Three panels trace each candidate: career slope, network position, and profile match.",
    objective: "",
    voiceover:
      "The Star Profiler distills four traits from Sailor Shift's pre-breakout years: output momentum, cross-genre reach, network centrality, and genre magnetism. Each candidate is scored across all four. Na Dai leads with a perfect 100 — profile similarity, network density, and career slope all confirm the match.",
    activePanels: ["profiler", "career", "galaxy"],
    insight: "This prediction is not intuition — it is a quantified comparison of profile, network, and trajectory.",
  },
];
