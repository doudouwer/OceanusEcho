import type {
  CareerTrackPayload,
  GenreFlowPayload,
  InfluenceGalaxyPayload,
  RisingStarsPayload,
} from "./api";
import type { PanelKey } from "./storyData";

export type PanelInsight = {
  headline: string;
  bullets: string[];
  callout?: string;
};

function fmt(n: number, dec = 0) {
  return n.toLocaleString("en", {
    minimumFractionDigits: dec,
    maximumFractionDigits: dec,
  });
}

function safeScore(v: number | undefined) {
  return typeof v === "number" && !isNaN(v) ? v : 0;
}

// ─── Career Arc ────────────────────────────────────────────────────────────────

export function computeCareerInsights(
  data: CareerTrackPayload,
  actId: number,
): PanelInsight {
  const byYear = data.by_year ?? [];
  const songs = byYear.map((y) => y.song_count);
  const notables = byYear.map((y) => y.notable_count);
  const total = safeScore(data.summary?.total_works);
  const peakYear = data.summary?.peak_year;
  const firstNotable = data.summary?.first_notable_year;
  const fameGap = safeScore(data.summary?.fame_gap_years ?? undefined);
  const span = safeScore(data.summary?.active_span_years);
  const years = byYear.map((y) => y.year);
  const peakSong = Math.max(...songs, 0);
  const peakIdx = songs.indexOf(peakSong);

  const yearRange =
    years.length >= 2 ? `${years[0]}–${years[years.length - 1]}` : "N/A";

  const headline =
    actId === 3
      ? "Trajectory Comparison"
      : peakYear
        ? `Career peaked in ${peakYear}`
        : "Career trajectory";

  const bullets: string[] = [];

  if (actId === 1) {
    const deltas = songs.map((s, i) => (i === 0 ? 0 : s - songs[i - 1]));
    const maxDelta = Math.max(...deltas);
    const spikeIdx = deltas.indexOf(maxDelta);
    const spikeYear = years[spikeIdx];

    bullets.push(
      `${fmt(total)} total works across ${span} active years (${yearRange}).`,
    );

    if (peakYear) {
      bullets.push(
        `Peak output of ${fmt(peakSong)} songs in ${peakYear}.`,
      );
    }

    if (firstNotable) {
      bullets.push(
        `Notable tags begin in ${firstNotable}${
          fameGap > 0 ? `, ${fmt(fameGap)} years after first release` : ""
        }.`,
      );
    }

    if (spikeYear != null && peakYear != null && spikeYear !== peakYear) {
      bullets.push(
        `Sharpest single-year jump: +${fmt(maxDelta)} songs in ${spikeYear}.`,
      );
    }

    const notablePeak = Math.max(...notables, 0);
    if (notablePeak > 0 && peakIdx >= 0) {
      bullets.push(
        `Notable count peaks at ${fmt(notablePeak)} in ${byYear[peakIdx]?.year ?? "?"} — output and quality rise together.`,
      );
    }
  } else if (actId === 3) {
    const years = byYear.map((y) => y.year);
    const top3 = [...songs]
      .sort((a, b) => b - a)
      .slice(0, 3)
      .filter((v) => v > 0);
    const avg = songs.length > 0 ? songs.reduce((a, b) => a + b, 0) / songs.length : 0;

    bullets.push(
      `${fmt(total)} total works across ${span} active years.`,
    );
    if (peakYear) {
      bullets.push(
        `Peak: ${fmt(peakSong)} songs in ${peakYear}. Notable threshold crossed in ${firstNotable ?? "?"}.`,
      );
    }
    if (top3.length > 0) {
      bullets.push(
        `Top-3 output years: ${top3.join(", ")} songs. Average output: ${fmt(avg, 1)}/year.`,
      );
    }
  }

  return { headline, bullets };
}

// ─── Influence Galaxy ─────────────────────────────────────────────────────────

export function computeGalaxyInsights(
  data: InfluenceGalaxyPayload,
  actId: number,
  task1Relations: string[],
  focusNodeId?: string,
): PanelInsight {
  const nodes = data.graph?.nodes ?? [];
  const links = data.graph?.links ?? [];
  const bridges = data.bridge_nodes ?? [];
  const seeds = data.seed_people ?? [];

  const headline =
    actId === 3 && focusNodeId
      ? "Candidate's network"
      : actId === 2
        ? bridges.length > 0
          ? `${bridges[0].name} bridges two worlds`
          : "Cross-genre network"
        : "Influence network";

  const bullets: string[] = [];

  const filteredLinks =
    task1Relations.includes("ALL_RELATION")
      ? links
      : links.filter((l) => task1Relations.includes(l.type));

  if (actId === 1) {
    const memberLinks = links.filter((l) => l.type === "MEMBER_OF");
    const styleLinks = links.filter((l) => l.type === "IN_STYLE_OF");
    const performerLinks = links.filter((l) => l.type === "PERFORMER_OF");

    if (seeds.length > 0) {
      bullets.push(
        `${seeds[0].name} anchors the network with ${links.length} total connections.`,
      );
    }
    if (memberLinks.length > 0) {
      bullets.push(
        `${memberLinks.length} band/ensemble links reveal group affiliations.`,
      );
    }
    if (styleLinks.length > 0) {
      bullets.push(
        `${styleLinks.length} stylistic influence edges show stylistic peers.`,
      );
    }
    if (performerLinks.length > 0) {
      bullets.push(
        `${performerLinks.length} performance collaborations complete the picture.`,
      );
    }
    if (filteredLinks.length < links.length) {
      bullets.push(
        `Filter active: showing ${filteredLinks.length} of ${links.length} edges.`,
      );
    }
  } else if (actId === 2) {
    if (bridges.length > 0) {
      const top = [...bridges].sort((a, b) => b.bridge_score - a.bridge_score)[0];
      bullets.push(
        `${top.name} has the highest bridge score (${top.bridge_score.toFixed(2)}) — connecting Oceanus Folk with Indie Pop.`,
      );
      if (bridges.length > 1) {
        const top3 = bridges
          .slice()
          .sort((a, b) => b.degree - a.degree)
          .slice(0, 3);
        bullets.push(
          `Top bridge nodes by degree: ${top3.map((b) => b.name).join(", ")}.`,
        );
      }
    } else {
      bullets.push(
        `${nodes.length} nodes / ${links.length} edges in the Oceanus Folk / Indie Pop sphere.`,
      );
    }
  } else if (actId === 3 && focusNodeId) {
    const candidateLinks = links.filter(
      (l) => l.source === focusNodeId || l.target === focusNodeId,
    );
    const uniquePartners = new Set(
      candidateLinks.flatMap((l) =>
        l.source === focusNodeId ? [l.target] : [l.source],
      ),
    );
    const edgeTypes = [...new Set(candidateLinks.map((l) => l.type))];

    bullets.push(
      `${uniquePartners.size} direct collaborators; ${candidateLinks.length} total edges.`,
    );
    if (edgeTypes.length > 0) {
      bullets.push(`Relationship types present: ${edgeTypes.join(", ")}.`);
    }
    const highDegree = [...(data.bridge_nodes ?? [])]
      .filter((b) => b.node_id === focusNodeId)
      .pop();
    if (highDegree) {
      bullets.push(
        `Bridge score: ${highDegree.bridge_score.toFixed(2)}; degree: ${highDegree.degree}.`,
      );
    }
  }

  return { headline, bullets };
}

// ─── Genre Flow ────────────────────────────────────────────────────────────────

export function computeGenreInsights(
  data: GenreFlowPayload | undefined,
  task2Step: number,
  carouselIndex: number,
): PanelInsight {
  const series = data?.series ?? [];
  const oceanus = series.find((s) => s.genre === "Oceanus Folk");
  const oceanusPoints = oceanus?.points ?? [];
  const years = oceanusPoints.map((p) => p.year);
  const values = oceanusPoints.map((p) => p.value);

  const bullets: string[] = [];

  if (task2Step === 0) {
    // Growth curve — spike analysis
    const deltas = values.map((v, i) => (i === 0 ? 0 : v - values[i - 1]));
    const maxDelta = Math.max(...deltas);
    const spikeIdx = deltas.indexOf(maxDelta);
    const spikeYear = years[spikeIdx];
    const totalGrowth =
      values.length > 1 ? values[values.length - 1] - values[0] : 0;
    const spreadMode = maxDelta / Math.max(1, totalGrowth) >= 0.45 ? "Explosive" : "Gradual";

    if (spikeYear) {
      bullets.push(
        `Oceanus Folk shows ${spreadMode} diffusion: +${fmt(maxDelta)} works in ${spikeYear} alone.`,
      );
    }
    const peakIdx = values.indexOf(Math.max(...values, 0));
    if (peakIdx >= 0) {
      bullets.push(
        `Peak of ${fmt(values[peakIdx])} works in ${years[peakIdx]}.`,
      );
    }
    if (oceanusPoints.length > 1) {
      bullets.push(
        `Trajectory: ${fmt(values[0])} → ${fmt(values[values.length - 1])} works (${years[0]}–${years[years.length - 1]}).`,
      );
    }
    return {
      headline: spreadMode === "Explosive" ? "Explosive diffusion detected" : "Gradual diffusion pattern",
      bullets,
      callout:
        spreadMode === "Explosive"
          ? `The ${spikeYear} spike is the breakout signal — a single year drove the majority of total growth.`
          : "No single spike dominates; growth is distributed across multiple years.",
    };
  }

  if (task2Step === 1) {
    // Genre carousel — must match GenreFlow.tsx comparisonSeries sort exactly:
    // filter active points (value > 0, year >= 2015), Indie Pop first, then by total
    const otherSeries = series.filter(
      (s) => s.genre !== "Oceanus Folk" && s.points.some((p) => p.year >= 2015 && p.value > 0),
    );
    const totalOf = (s: typeof otherSeries[number]) =>
      s.points.filter((p) => p.year >= 2015 && p.value > 0).reduce((sum, p) => sum + p.value, 0);
    const sorted = [...otherSeries].sort((a, b) => {
      if (a.genre === "Indie Pop") return -1;
      if (b.genre === "Indie Pop") return 1;
      return totalOf(b) - totalOf(a);
    });
    const activeIdx = carouselIndex % Math.max(sorted.length, 1);
    const active = sorted[activeIdx];

    if (sorted.length > 0) {
      bullets.push(
        `${sorted.length} genres overlap with Oceanus Folk in this window.`,
      );
    }
    if (active) {
      const activePoints = active.points;
      const activeOverlap = activePoints.map((sp, i) =>
        Math.min(sp.value, oceanusPoints.find((op) => op.year === sp.year)?.value ?? 0),
      );
      const maxOverlap = Math.max(0, ...activeOverlap);
      const peakOverlapIdx = activeOverlap.indexOf(maxOverlap);
      bullets.push(
        `Carousel #${activeIdx + 1}: ${active.genre} — peak overlap of ${fmt(maxOverlap)} works in ${activePoints[peakOverlapIdx]?.year ?? "?"}.`,
      );
    }
    const top3 = sorted.slice(0, 3);
    if (top3.length > 1) {
      bullets.push(
        `Top overlap genres: ${top3.map((s) => {
          const pts = s.points;
          const mx = Math.max(0, ...pts.map((sp, i) => Math.min(sp.value, oceanusPoints.find((op) => op.year === sp.year)?.value ?? 0)));
          const py = pts[pts.findIndex((sp) => Math.min(sp.value, oceanusPoints.find((op) => op.year === sp.year)?.value ?? 0) === mx)]?.year;
          return `${s.genre} (${py})`;
        }).join(", ")}.`,
      );
    }
    return {
      headline: sorted.length > 0 ? `${sorted[0].genre} leads overlap` : "No significant genre overlap",
      bullets,
    };
  }

  // Sankey — style edges
  if (!data) return { headline: "No data", bullets: ["Genre flow data is not available."] };
  const nodes = data.nodes ?? [];
  const links = (data.links ?? []).filter((l) => l.value > 0);
  const sourceNode = nodes.find((n) => n.id === "Oceanus Folk")?.name ?? "Oceanus Folk";
  const connected = links
    .filter((l) => l.source === "Oceanus Folk" || l.target === "Oceanus Folk")
    .map((l) => ({
      target: nodes.find((n) => n.id === (l.source === "Oceanus Folk" ? l.target : l.source))?.name ?? "Unknown",
      value: l.value,
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 6);

  const totalFlow = connected.reduce((sum, l) => sum + l.value, 0);

  if (connected.length > 0) {
    bullets.push(
      `${sourceNode} flows into ${connected.length} neighboring genre styles.`,
    );
    bullets.push(
      `Total style-edge value: ${fmt(totalFlow)} across all flows.`,
    );
    const top = connected[0];
    bullets.push(
      `Strongest flow: ${top.target} (value ${fmt(top.value)}, ${((top.value / Math.max(1, totalFlow)) * 100).toFixed(0)}% of total).`,
    );
    if (connected.length > 1) {
      const runnersUp = connected.slice(1, 3).map((l) => l.target).join(", ");
      bullets.push(`Other strong flows: ${runnersUp}.`);
    }
  } else {
    bullets.push("No style-edge flows found for Oceanus Folk in this window.");
  }

  return {
    headline: connected.length > 0 ? `${connected[0].target} dominates style flows` : "Sparse style-edge network",
    bullets,
  };
}

// ─── Star Profiler ─────────────────────────────────────────────────────────────

export function computeProfilerInsights(
  data: InfluenceGalaxyPayload,
  rising: RisingStarsPayload,
  focusCandidateId?: string,
  settled = false,
): PanelInsight {
  const candidates = rising.candidates.slice(0, 8);
  const top = candidates[0];
  const focus = candidates.find((c) => c.person_id === focusCandidateId) ?? top;
  const links = data.graph?.links ?? [];

  const bullets: string[] = [];

  if (!focus) {
    return { headline: "No candidate data", bullets };
  }

  bullets.push(
    `${focus.name} ranked #${candidates.findIndex((c) => c.person_id === focus.person_id) + 1} with a similarity score of ${safeScore(focus.score).toFixed(0)}.`,
  );

  const relatedLinks = links.filter(
    (l) => l.source === focus.person_id || l.target === focus.person_id,
  );
  const collaborators = new Set(
    relatedLinks.flatMap((l) =>
      l.source === focus.person_id ? [l.target] : [l.source],
    ),
  );
  const edgeTypes = [...new Set(relatedLinks.map((l) => l.type))];

  if (collaborators.size > 0) {
    bullets.push(
      `${collaborators.size} direct collaborators in the network; ${relatedLinks.length} total edges.`,
    );
    bullets.push(`Collaboration types: ${edgeTypes.join(", ")}.`);
  }

  const metrics = focus.metrics ?? {};
  const topMetric = Object.entries(metrics).sort(([, a], [, b]) => safeScore(b) - safeScore(a))[0];
  if (topMetric) {
    bullets.push(
      `Strongest metric: ${topMetric[0]} = ${safeScore(topMetric[1]).toFixed(2)}.`,
    );
  }

  return {
    headline: settled
      ? `Final match: ${focus.name}`
      : `Comparing candidates`,
    bullets,
    callout: settled
      ? `${focus.name} most closely mirrors Sailor Shift's pre-breakout profile across all dimensions.`
      : `Next candidate will appear in ~2 seconds…`,
  };
}

// ─── Main dispatcher ────────────────────────────────────────────────────────────

export type ComputedInsights = Partial<Record<PanelKey, PanelInsight>>;

export function computePanelInsights(
  panelKey: PanelKey,
  actId: number,
  state: {
    career?: CareerTrackPayload;
    galaxy?: InfluenceGalaxyPayload;
    genre?: GenreFlowPayload;
    genreSankey?: GenreFlowPayload;
    rising?: RisingStarsPayload;
  },
  extra: {
    task1Relations: string[];
    task2Step: number;
    carouselIndex?: number;
    task3CandidateId?: string;
    task3Settled: boolean;
  },
): PanelInsight | null {
  switch (panelKey) {
    case "career":
      if (!state.career) return null;
      return computeCareerInsights(state.career, actId);
    case "galaxy":
      if (!state.galaxy) return null;
      return computeGalaxyInsights(
        state.galaxy,
        actId,
        extra.task1Relations,
        extra.task3CandidateId,
      );
    case "genre":
      return computeGenreInsights(
        extra.task2Step === 2 ? state.genreSankey : state.genre,
        extra.task2Step,
        extra.carouselIndex ?? 0,
      );
    case "profiler":
      if (!state.galaxy || !state.rising) return null;
      return computeProfilerInsights(
        state.galaxy,
        state.rising,
        extra.task3CandidateId,
        extra.task3Settled,
      );
  }
}
