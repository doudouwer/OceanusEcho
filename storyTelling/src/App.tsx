import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import {
  fetchCareerTrack,
  fetchGenreFlow,
  fetchInfluenceSubgraph,
  fetchPersonProfile,
  fetchRisingStars,
  type CareerTrackPayload,
  type GenreFlowPayload,
  type InfluenceGalaxyPayload,
  type PersonProfilePayload,
  type RisingStarsPayload,
} from "./api";
import {
  acts,
  type Act,
  type PanelKey,
} from "./storyData";

const panelLabels: Record<PanelKey, string> = {
  career: "Career Arc",
  galaxy: "Influence Galaxy",
  genre: "Genre Flow",
  profiler: "Star Profiler",
};

const panelOrder: PanelKey[] = ["career", "galaxy", "genre", "profiler"];
const SAILOR_ID = "17255";
const CAREER_START_YEAR = 2020;
const YEAR_RANGE = [2023, 2040] as const;
const TASK2_OCEANUS_START_YEAR = 2020;
const TASK2_FUSION_START_YEAR = 2015;
const TASK3_CANDIDATE_COUNT = 8;
const task1RelationOptions = ["IN_STYLE_OF", "MEMBER_OF", "PERFORMER_OF", "ALL_RELATION"] as const;
type Task1RelationFilter = (typeof task1RelationOptions)[number];
const task2PanelSteps: PanelKey[] = ["genre", "genre", "genre"];
const task2Scenes = [
  {
    title: "第一幕：爆炸还是渐进？",
    panelTitle: "Explosion or gradual spread",
    panelDescription: "全局流派筛选锁定 Oceanus Folk，用面积厚度与年度增量判断是 Spike 还是 Gradual。",
    action: "Filter: Oceanus Folk only",
    narration: "如果 Oceanus Folk 在短期内陡直上升，就把它定性为 Explosive；如果是多年缓慢增厚，则是 Gradual。",
  },
  {
    title: "第二幕：跨流派的演变轨迹",
    panelTitle: "Oceanus Folk genre carousel",
    panelDescription: "以 Oceanus Folk 为固定基准，轮播叠加所有其他流派，寻找最明显的交汇时间窗。",
    action: "Carousel: Oceanus Folk + all genres",
    narration: "当 Oceanus Folk 与某个流派在同一年份同时增厚，故事从单一流派扩散转向跨流派融合。",
  },
  {
    title: "第三幕：流派桑基中的扩散路径",
    panelTitle: "Oceanus Folk sankey spread",
    panelDescription: "用桑基图把 Oceanus Folk 连接到共同出现强度最高的流派，观察它扩散到哪些风格生态。",
    action: "Sankey: Oceanus Folk → top genres",
    narration: "不再追到具体节点，而是回到宏观流派层面，看 Oceanus Folk 最强地流向了哪些相邻风格。",
  },
] as const;

type StoryState = {
  status: "loading" | "ready" | "error";
  error?: string;
  career?: CareerTrackPayload;
  rookieCareers?: CareerTrackPayload[];
  genre?: GenreFlowPayload;
  genreSankey?: GenreFlowPayload;
  galaxy?: InfluenceGalaxyPayload;
  profiles?: PersonProfilePayload;
  rising?: RisingStarsPayload;
};

export default function App() {
  const [activeActId, setActiveActId] = useState(1);
  const [task1Step, setTask1Step] = useState(0);
  const [task2Step, setTask2Step] = useState(0);
  const [task3CandidateIndex, setTask3CandidateIndex] = useState(0);
  const [task3Settled, setTask3Settled] = useState(false);
  const [task1Relations, setTask1Relations] = useState<Task1RelationFilter[]>(["ALL_RELATION"]);
  const [storyState, setStoryState] = useState<StoryState>({ status: "loading" });
  const activeAct = acts.find((act) => act.id === activeActId) ?? acts[0];
  const visiblePanels = panelOrder.filter((panelKey) => activeAct.activePanels.includes(panelKey));
  const task3Candidates = storyState.rising?.candidates.slice(0, TASK3_CANDIDATE_COUNT) ?? [];
  const task3Candidate = activeActId === 3 ? task3Candidates[Math.min(task3CandidateIndex, Math.max(task3Candidates.length - 1, 0))] : undefined;
  const currentPanels =
    activeActId === 1
      ? [activeAct.activePanels[task1Step] ?? "career"]
      : activeActId === 2
        ? [task2PanelSteps[task2Step] ?? "genre"]
        : visiblePanels;

  useEffect(() => {
    let cancelled = false;
    setStoryState({ status: "loading" });

    async function loadActData() {
      try {
        const loaded = await fetchActData(activeActId);
        if (!cancelled) setStoryState({ status: "ready", ...loaded });
      } catch (error) {
        if (!cancelled) {
          setStoryState({
            status: "error",
            error: error instanceof Error ? error.message : "Unknown API error",
          });
        }
      }
    }

    void loadActData();
    setTask1Step(0);
    setTask2Step(0);
    setTask3CandidateIndex(0);
    setTask3Settled(false);
    return () => {
      cancelled = true;
    };
  }, [activeActId]);

  useEffect(() => {
    if (activeActId !== 3 || storyState.status !== "ready" || !storyState.rising?.candidates.length) return undefined;

    const count = Math.min(TASK3_CANDIDATE_COUNT, storyState.rising.candidates.length);
    setTask3CandidateIndex(0);
    setTask3Settled(false);
    if (count <= 1) {
      setTask3Settled(true);
      return undefined;
    }

    let index = 0;
    const timer = window.setInterval(() => {
      index += 1;
      if (index < count) {
        setTask3CandidateIndex(index);
        return;
      }
      setTask3CandidateIndex(0);
      setTask3Settled(true);
      window.clearInterval(timer);
    }, 2000);

    return () => window.clearInterval(timer);
  }, [activeActId, storyState.status, storyState.rising]);

  return (
    <div className="shell">
      <header className="hero">
        <div className="brand">
          <span className="brandMark" />
          <div>
            <p className="eyebrow">OceanusEcho StoryTelling</p>
            <h1>三幕式数据叙事展示</h1>
            <p className="heroCopy">
              根据 `StoryTellingScript.md` 的叙事路线，把四个 dashboard panel 组织成可演示的三幕故事。
            </p>
          </div>
        </div>
        <div className="statusCard">
          <span>Active Panels</span>
          <strong>{currentPanels.map((key) => panelLabels[key]).join(" / ")}</strong>
        </div>
      </header>

      <main className="storyGrid">
        <aside className="storyRail">
          <ActSelector activeActId={activeActId} onSelect={setActiveActId} />
          <Narration act={activeAct} actStep={activeActId === 2 ? task2Step : undefined} />
        </aside>

        <section key={`${activeAct.id}-${storyState.status}-${task1Step}-${task2Step}`} className={`dashboardGrid act-${activeAct.id} panels-${currentPanels.length}`}>
          {currentPanels.map((panelKey, index) =>
            renderPanel(panelKey, activeAct.id, index, storyState, task1Relations, setTask1Relations, task2Step, task3Candidate?.person_id, task3Settled),
          )}
          {activeActId === 1 && (
            <button
              type="button"
              className="storyArrow"
              aria-label={task1Step === 0 ? "切换到 Influence network" : "返回 Career timeline"}
              onClick={() => setTask1Step((step) => (step === 0 ? 1 : 0))}
            >
              <span>{task1Step === 0 ? "↓" : "↑"}</span>
              {task1Step === 0 ? "Influence network" : "Career timeline"}
            </button>
          )}
          {activeActId === 2 && (
            <button
              type="button"
              className="storyArrow"
              aria-label={`切换到 ${task2Scenes[(task2Step + 1) % task2Scenes.length].title}`}
              onClick={() => setTask2Step((step) => (step + 1) % task2Scenes.length)}
            >
              <span>↓</span>
              {task2Step === 0 ? "Add Indie Pop" : task2Step === 1 ? "Sankey spread" : "Back to spread"}
            </button>
          )}
        </section>
      </main>
    </div>
  );
}

async function fetchActData(actId: number): Promise<Omit<StoryState, "status" | "error">> {
  if (actId === 1) {
    const [career, galaxy] = await Promise.all([
      fetchCareerTrack(SAILOR_ID, CAREER_START_YEAR, YEAR_RANGE[1]),
      fetchInfluenceSubgraph({
        startYear: 1900,
        endYear: 2200,
        genres: [],
        seedPersonIds: [SAILOR_ID],
        relTypes: [],
        limitNodes: 160,
      }),
    ]);
    return { career, galaxy };
  }

  if (actId === 2) {
    const [genre, genreSankey, galaxy] = await Promise.all([
      fetchGenreFlow(TASK2_FUSION_START_YEAR, YEAR_RANGE[1]),
      fetchGenreFlow(TASK2_FUSION_START_YEAR, YEAR_RANGE[1], {
        metric: "style_edges",
        sourceGenre: "Oceanus Folk",
        limit: 100,
      }),
      fetchInfluenceSubgraph({
        startYear: YEAR_RANGE[0],
        endYear: YEAR_RANGE[1],
        genres: ["Oceanus Folk", "Indie Pop"],
        seedPersonIds: [],
        relTypes: ["IN_STYLE_OF", "PERFORMER_OF", "COMPOSER_OF", "PRODUCER_OF"],
        limitNodes: 220,
      }),
    ]);
    return { genre, genreSankey, galaxy };
  }

  const rising = await fetchRisingStars(YEAR_RANGE[0], YEAR_RANGE[1], TASK3_CANDIDATE_COUNT);
  const candidateIds = rising.candidates.slice(0, TASK3_CANDIDATE_COUNT).map((candidate) => candidate.person_id);
  const [career, profiles, galaxy, ...rookieCareers] = await Promise.all([
    fetchCareerTrack(SAILOR_ID, CAREER_START_YEAR, YEAR_RANGE[1]),
    fetchPersonProfile([SAILOR_ID, ...candidateIds], YEAR_RANGE[0], YEAR_RANGE[1]),
    fetchInfluenceSubgraph({
      startYear: YEAR_RANGE[0],
      endYear: YEAR_RANGE[1],
      genres: ["Oceanus Folk", "Indie Pop"],
      seedPersonIds: candidateIds,
      relTypes: ["PERFORMER_OF", "COMPOSER_OF", "PRODUCER_OF", "IN_STYLE_OF"],
      limitNodes: 280,
    }),
    ...candidateIds.map((id) => fetchCareerTrack(id, CAREER_START_YEAR, YEAR_RANGE[1])),
  ]);
  return { career, profiles, galaxy, rising, rookieCareers };
}

function renderPanel(
  panelKey: PanelKey,
  actId: number,
  index: number,
  state: StoryState,
  task1Relations: Task1RelationFilter[],
  setTask1Relations: (relations: Task1RelationFilter[]) => void,
  task2Step: number,
  task3CandidateId?: string,
  task3Settled = false,
) {
  const delayStyle = { animationDelay: `${index * 120}ms` };
  const task2Scene = task2Scenes[task2Step] ?? task2Scenes[0];
  const selectedRookieCareer = state.rookieCareers?.find((track) => track.person.id === task3CandidateId);
  switch (panelKey) {
    case "career":
      return (
        <PanelFrame
          key={panelKey}
          panelKey="career"
          title="Career timeline"
          description="Sailor Shift 的作品频率、Notable 爆发点，以及 Rising Star 早期轨迹对照。"
          style={delayStyle}
        >
          {state.status !== "ready" ? (
            <PanelState state={state} />
          ) : (
            <CareerArc
              actId={actId}
              data={state.career}
              rookieData={actId === 3 && selectedRookieCareer ? [selectedRookieCareer] : state.rookieCareers}
              focusCandidateId={actId === 3 ? task3CandidateId : undefined}
              settled={task3Settled}
            />
          )}
        </PanelFrame>
      );
    case "galaxy":
      return (
        <PanelFrame
          key={panelKey}
          panelKey="galaxy"
          title={actId === 2 ? task2Scene.panelTitle : "Influence network"}
          description={actId === 2 ? task2Scene.panelDescription : "以 Sailor Shift / Ivy Echoes / Bridge Nodes 为核心的关系网络叙事。"}
          style={delayStyle}
        >
          {state.status !== "ready" ? (
            <PanelState state={state} />
          ) : (
            <InfluenceGalaxy
              actId={actId}
              data={state.galaxy}
              relationFilter={actId === 1 ? task1Relations : ["ALL_RELATION"]}
              onRelationFilterChange={actId === 1 ? setTask1Relations : undefined}
              focusNodeId={actId === 3 ? task3CandidateId : undefined}
              settled={task3Settled}
            />
          )}
        </PanelFrame>
      );
    case "genre":
      return (
        <PanelFrame
          key={panelKey}
          panelKey="genre"
          title={actId === 2 ? task2Scene.panelTitle : "Genre evolution"}
          description={actId === 2 ? task2Scene.panelDescription : "Oceanus Folk 与 Indie Pop 的扩散、交汇和爆发式增长。"}
          style={delayStyle}
        >
          {state.status !== "ready" ? (
            <PanelState state={state} />
          ) : (
            <GenreFlow
              data={actId === 2 && task2Step === 2 ? state.genreSankey : state.genre}
              mode={actId === 2 && task2Step === 0 ? "oceanus" : actId === 2 && task2Step === 2 ? "sankey" : "fusion"}
            />
          )}
        </PanelFrame>
      );
    case "profiler":
      return (
        <PanelFrame
          key={panelKey}
          panelKey="profiler"
          title="Artist profile"
          description="巨星模型与新人候选的雷达画像，用于定义和预测 Rising Star。"
          style={delayStyle}
        >
          {state.status !== "ready" ? (
            <PanelState state={state} />
          ) : (
            <StarProfiler profiles={state.profiles} rising={state.rising} focusCandidateId={actId === 3 ? task3CandidateId : undefined} settled={task3Settled} />
          )}
        </PanelFrame>
      );
  }
}

function PanelState({ state }: { state: StoryState }) {
  return (
    <div className={state.status === "error" ? "panelState error" : "panelState"}>
      {state.status === "error" ? `数据加载失败：${state.error}` : "正在从 FastAPI / Neo4j 加载真实数据..."}
    </div>
  );
}

function ActSelector({
  activeActId,
  onSelect,
}: {
  activeActId: number;
  onSelect: (actId: number) => void;
}) {
  return (
    <div className="actSelector">
      {acts.map((act) => (
        <button
          key={act.id}
          type="button"
          className={act.id === activeActId ? "actButton active" : "actButton"}
          onClick={() => onSelect(act.id)}
        >
          <span>{act.kicker}</span>
          <strong>{act.title}</strong>
        </button>
      ))}
    </div>
  );
}

function Narration({ act, actStep }: { act: Act; actStep?: number }) {
  const scene = act.id === 2 && actStep !== undefined ? task2Scenes[actStep] : undefined;
  return (
    <article className="narration">
      <p className="eyebrow">{act.kicker}</p>
      <h2>{act.title}</h2>
      <p className="subtitle">{act.subtitle}</p>
      {scene && (
        <div className="sceneCue">
          <span>{scene.action}</span>
          <strong>{scene.title}</strong>
          <p>{scene.narration}</p>
        </div>
      )}
      <div className="objective">
        <span>Objective</span>
        <p>{act.objective}</p>
      </div>
      <div className="scriptBlock">
        <span>Voiceover</span>
        <p>{act.voiceover}</p>
      </div>
      <ol>
        {act.actions.map((action) => (
          <li key={action}>{action}</li>
        ))}
      </ol>
      <p className="insight">{act.insight}</p>
    </article>
  );
}

function PanelFrame({
  panelKey,
  title,
  description,
  children,
  style,
}: {
  panelKey: PanelKey;
  title: string;
  description: string;
  children: ReactNode;
  style?: CSSProperties;
}) {
  return (
    <article className={`panel panel-${panelKey}`} style={style}>
      <header className="panelHead">
        <h3>{title}</h3>
        <span>{panelLabels[panelKey]}</span>
      </header>
      <p className="panelDesc">{description}</p>
      <div className="panelBody">{children}</div>
    </article>
  );
}

function CareerArc({
  actId,
  data,
  rookieData = [],
  focusCandidateId,
  settled = false,
}: {
  actId: number;
  data?: CareerTrackPayload;
  rookieData?: CareerTrackPayload[];
  focusCandidateId?: string;
  settled?: boolean;
}) {
  if (!data?.by_year?.length) {
    return <div className="panelState">当前时间窗没有职业轨迹数据。</div>;
  }

  const years = buildYearRange([data, ...rookieData]);
  const songValues = years.map((year) => data.by_year.find((item) => item.year === year)?.song_count ?? 0);
  const notableValues = years.map((year) => data.by_year.find((item) => item.year === year)?.notable_count ?? 0);
  const rookieValues = rookieData.map((rookie) => ({
    name: rookie.person.name,
    values: years.map((year) => rookie.by_year.find((item) => item.year === year)?.song_count ?? 0),
  }));
  const maxValue = Math.max(1, ...songValues, ...notableValues, ...rookieValues.flatMap((rookie) => rookie.values));
  const chart = {
    left: 44,
    right: 18,
    top: 22,
    bottom: 34,
    width: 520,
    height: 230,
  };
  const plotWidth = chart.width - chart.left - chart.right;
  const plotHeight = chart.height - chart.top - chart.bottom;
  const point = (value: number, index: number, total: number) => {
    const x = chart.left + (plotWidth * index) / Math.max(total - 1, 1);
    const y = chart.top + plotHeight - (value / maxValue) * plotHeight;
    return { x, y, value: `${x},${y}` };
  };

  const songPath = songValues.map((value, index) => point(value, index, years.length).value).join(" ");
  const notablePath = notableValues.map((value, index) => point(value, index, years.length).value).join(" ");
  const showRookies = actId === 3;
  const highlightStart = data.summary?.first_notable_year ?? data.summary?.peak_year ?? years[Math.max(0, years.length - 3)];
  const highlightEnd = data.summary?.peak_year ?? years[years.length - 1];

  return (
    <div className="chartWrap">
      <svg key={showRookies ? `career-${focusCandidateId ?? "candidate"}` : "career"} viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-label="Career Arc">
        <Grid chart={chart} />
        <polyline points={songPath} className="linePrimary" />
        <polyline points={notablePath} className="lineDashed" />
        {years.map((year, index) => {
          const p = point(songValues[index], index, years.length);
          const isHot = year >= highlightStart && year <= highlightEnd && actId === 1;
          return (
          <g key={year}>
            <circle
              cx={p.x}
              cy={p.y}
              r={isHot ? 5.5 : 3.5}
              className={isHot ? "hotDot" : "dot"}
              style={{ animationDelay: `${520 + index * 70}ms` }}
            />
            {index % 2 === 0 && (
              <text x={chart.left + (plotWidth * index) / Math.max(years.length - 1, 1)} y={218}>
                {year}
              </text>
            )}
          </g>
        );})}
        {showRookies &&
          rookieValues.map((rookie, lineIndex) => (
            <polyline
              key={rookie.name}
              points={rookie.values.map((value, index) => point(value, index, years.length).value).join(" ")}
              className={`rookieLine rookie${lineIndex}`}
              style={{ animationDelay: `${760 + lineIndex * 140}ms` }}
            />
          ))}
      </svg>
      <div className="legendRow">
        <span><i className="swatch cyan" /> {data.person.name} works</span>
        <span><i className="swatch gold" /> Notable</span>
        {showRookies && <span><i className="swatch green" /> {rookieData[0]?.person.name ?? "Rising candidate"}</span>}
        {showRookies && focusCandidateId && <span>{settled ? "Final match" : "Comparing"} · #{focusCandidateId}</span>}
      </div>
    </div>
  );
}

function buildYearRange(tracks: Array<CareerTrackPayload | undefined>) {
  const allYears = tracks.flatMap((track) => track?.by_year.map((item) => item.year) ?? []);
  const min = Math.min(CAREER_START_YEAR, ...allYears);
  const max = Math.max(...allYears);
  return Array.from({ length: max - min + 1 }, (_, index) => min + index);
}

function Grid({ chart }: { chart: { left: number; right: number; top: number; bottom: number; width: number; height: number } }) {
  const rows = [0, 1, 2, 3, 4];
  return (
    <g className="gridLines">
      {rows.map((row) => {
        const y = chart.top + ((chart.height - chart.top - chart.bottom) * row) / (rows.length - 1);
        return <line key={row} x1={chart.left} x2={chart.width - chart.right} y1={y} y2={y} />;
      })}
    </g>
  );
}

function InfluenceGalaxy({
  actId,
  data,
  relationFilter,
  onRelationFilterChange,
  focusNodeId,
  settled = false,
}: {
  actId: number;
  data?: InfluenceGalaxyPayload;
  relationFilter: Task1RelationFilter[];
  onRelationFilterChange?: (relations: Task1RelationFilter[]) => void;
  focusNodeId?: string;
  settled?: boolean;
}) {
  const allLinks = data?.graph.links ?? [];
  const filteredLinks = relationFilter.includes("ALL_RELATION")
    ? allLinks
    : allLinks.filter((link) => relationFilter.includes(link.type as Task1RelationFilter));
  const connectedNodeIds = new Set<string>();
  filteredLinks.forEach((link) => {
    connectedNodeIds.add(link.source);
    connectedNodeIds.add(link.target);
  });
  data?.seed_people?.forEach((person) => connectedNodeIds.add(person.id));
  if (focusNodeId) connectedNodeIds.add(focusNodeId);
  const bridgeIds = new Set((data?.bridge_nodes ?? []).map((node) => node.node_id));
  const seedIds = new Set((data?.seed_people ?? []).map((person) => person.id));
  const nodes = (data?.graph.nodes ?? [])
    .filter((node) => connectedNodeIds.has(node.id))
    .sort((a, b) => {
      const score = (nodeId: string) =>
        (nodeId === focusNodeId ? 5 : 0) + (seedIds.has(nodeId) ? 3 : 0) + (bridgeIds.has(nodeId) ? 2 : 0);
      return score(b.id) - score(a.id);
    })
    .slice(0, 34);
  const nodeIds = new Set(nodes.map((node) => node.id));
  const links = filteredLinks.filter((link) => nodeIds.has(link.source) && nodeIds.has(link.target)).slice(0, 60);
  const positioned = layoutNodes(nodes);
  const visibleBridgeNames = (data?.bridge_nodes ?? [])
    .filter((node) => nodeIds.has(node.node_id))
    .slice(0, 3)
    .map((node) => node.name);

  if (!nodes.length) {
    return <div className="panelState">当前筛选下没有关系网络数据。</div>;
  }

  return (
    <div className="galaxyWrap">
      {onRelationFilterChange && (
        <RelationFilterBar selected={relationFilter} onChange={onRelationFilterChange} />
      )}
      <svg key={focusNodeId ? `galaxy-${focusNodeId}` : "galaxy"} viewBox="0 0 100 100" role="img" aria-label="Influence Galaxy">
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2.4" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        {links.map((link, index) => {
          const a = positioned.find((node) => node.id === link.source);
          const b = positioned.find((node) => node.id === link.target);
          if (!a || !b) return null;
          const active =
            actId === 3 && focusNodeId
              ? link.source === focusNodeId || link.target === focusNodeId
              : actId === 2
              ? bridgeIds.has(link.source) || bridgeIds.has(link.target) || link.type === "IN_STYLE_OF"
              : seedIds.has(link.source) || seedIds.has(link.target) || link.type === "MEMBER_OF";
          return (
            <line
              key={`${link.source}-${link.target}-${link.type}-${index}`}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              className={active ? "galaxyLink active" : "galaxyLink"}
              style={{ animationDelay: `${index * 110}ms` }}
            />
          );
        })}
        {positioned.map((node, index) => {
          const active =
            actId === 3 && focusNodeId
              ? node.id === focusNodeId
              : seedIds.has(node.id) || bridgeIds.has(node.id) || (actId === 1 && node.name === "Sailor Shift");
          const label = node.name || node.id;
          return (
            <g
              key={node.id}
              className={active ? "nodeGroup active" : "nodeGroup"}
              style={{ animationDelay: `${280 + index * 95}ms` }}
            >
              <circle cx={node.x} cy={node.y} r={node.label === "Person" || node.label === "MusicalGroup" ? 1.7 : 1.3} filter={active ? "url(#glow)" : undefined} />
              {active && <text x={node.x} y={node.y + 4}>{label}</text>}
            </g>
          );
        })}
      </svg>
      <div className="networkNotes">
        {relationFilter.map((rel) => <span key={rel}>{rel}</span>)}
        {actId === 2 && visibleBridgeNames.length > 0 && <span>Bridge: {visibleBridgeNames.join(" / ")}</span>}
        {actId === 3 && focusNodeId && <span>{settled ? "Final match" : "Comparing"} network focus</span>}
        <span>{nodes.length} nodes / {links.length} edges</span>
      </div>
    </div>
  );
}

function RelationFilterBar({
  selected,
  onChange,
}: {
  selected: Task1RelationFilter[];
  onChange: (relations: Task1RelationFilter[]) => void;
}) {
  const toggle = (relation: Task1RelationFilter) => {
    if (relation === "ALL_RELATION") {
      onChange(["ALL_RELATION"]);
      return;
    }

    const withoutAll = selected.filter((item) => item !== "ALL_RELATION");
    const next = withoutAll.includes(relation)
      ? withoutAll.filter((item) => item !== relation)
      : [...withoutAll, relation];
    onChange(next.length ? next : ["ALL_RELATION"]);
  };

  return (
    <div className="relationFilterBar" aria-label="Task 1 relation filters">
      {task1RelationOptions.map((relation) => (
        <label key={relation} className={selected.includes(relation) ? "relationChip active" : "relationChip"}>
          <input
            type="checkbox"
            checked={selected.includes(relation)}
            onChange={() => toggle(relation)}
          />
          <span>{relation}</span>
        </label>
      ))}
    </div>
  );
}

function layoutNodes(nodes: NonNullable<InfluenceGalaxyPayload["graph"]>["nodes"]) {
  if (nodes.length === 1) return [{ ...nodes[0], x: 50, y: 50 }];
  return nodes.map((node, index) => {
    if (node.name === "Sailor Shift" || node.id === SAILOR_ID) return { ...node, x: 50, y: 50 };
    const ring = index < 12 ? 27 : 39;
    const angle = -Math.PI / 2 + (index * 2.399963229728653) % (Math.PI * 2);
    return {
      ...node,
      x: 50 + Math.cos(angle) * ring,
      y: 50 + Math.sin(angle) * ring * 0.78,
    };
  });
}

function GenreFlow({ data, mode = "fusion" }: { data?: GenreFlowPayload; mode?: "oceanus" | "fusion" | "sankey" }) {
  const [carouselIndex, setCarouselIndex] = useState(0);
  const startYear = mode === "oceanus" ? TASK2_OCEANUS_START_YEAR : TASK2_FUSION_START_YEAR;
  const series = data?.series ?? [];
  const oceanus = series.find((item) => item.genre === "Oceanus Folk");
  const comparisonSeries = series
    .filter((item) => item.genre !== "Oceanus Folk" && item.points.some((point) => point.year >= startYear && point.value > 0))
    .sort((a, b) => {
      if (a.genre === "Indie Pop") return -1;
      if (b.genre === "Indie Pop") return 1;
      const total = (item: typeof a) =>
        item.points.filter((point) => point.year >= startYear).reduce((sum, point) => sum + point.value, 0);
      return total(b) - total(a);
    });
  const activeCompare = mode === "fusion" ? comparisonSeries[carouselIndex % Math.max(comparisonSeries.length, 1)] : undefined;

  useEffect(() => {
    setCarouselIndex(0);
  }, [mode, data]);

  useEffect(() => {
    if (mode !== "fusion" || comparisonSeries.length <= 1) return undefined;
    const timer = window.setInterval(() => {
      setCarouselIndex((index) => (index + 1) % comparisonSeries.length);
    }, 2400);
    return () => window.clearInterval(timer);
  }, [comparisonSeries.length, mode]);

  if (mode === "sankey") {
    return <GenreSankey data={data} startYear={startYear} />;
  }

  if (!oceanus?.points.length || (mode === "fusion" && !activeCompare?.points.length)) {
    return <div className="panelState">当前时间窗没有 Oceanus Folk 流派数据。</div>;
  }

  const yearSet = new Set<number>();
  oceanus?.points.filter((point) => point.year >= startYear).forEach((point) => yearSet.add(point.year));
  if (mode === "fusion") {
    comparisonSeries.forEach((item) => {
      item.points.filter((point) => point.year >= startYear).forEach((point) => yearSet.add(point.year));
    });
  }
  const years = [...yearSet].sort((a, b) => a - b);
  if (!years.length) {
    return <div className="panelState">当前时间窗没有 {startYear} 年之后的 Oceanus Folk / Indie Pop 流派数据。</div>;
  }
  const oceanusByYear = new Map(oceanus?.points.map((point) => [point.year, point.value]) ?? []);
  const compareByYear = new Map(activeCompare?.points.map((point) => [point.year, point.value]) ?? []);
  const rows = years.map((year) => ({
    year,
    oceanus: oceanusByYear.get(year) ?? 0,
    compare: compareByYear.get(year) ?? 0,
  }));
  const width = 520;
  const height = 230;
  const left = 44;
  const bottom = 34;
  const top = 22;
  const plotWidth = width - left - 18;
  const plotHeight = height - top - bottom;
  const max = Math.max(1, ...rows.flatMap((row) => (mode === "fusion" ? [row.oceanus, row.compare] : [row.oceanus])));
  const toX = (index: number) => left + (plotWidth * index) / Math.max(rows.length - 1, 1);
  const toY = (value: number) => top + plotHeight - (value / max) * plotHeight;
  const oceanusTop = rows.map((row, index) => `${toX(index)},${toY(row.oceanus)}`).join(" ");
  const compareTop = rows.map((row, index) => `${toX(index)},${toY(row.compare)}`).join(" ");
  const base = rows.map((_, index) => `${toX(index)},${top + plotHeight}`).reverse().join(" ");
  const deltas = rows.map((row, index) => (index === 0 ? 0 : row.oceanus - rows[index - 1].oceanus));
  const spikeIndex = Math.max(0, deltas.indexOf(Math.max(...deltas)));
  const spikeYear = rows[spikeIndex]?.year;
  const maxDelta = Math.max(0, ...deltas);
  const totalGrowth = Math.max(1, (rows[rows.length - 1]?.oceanus ?? 0) - (rows[0]?.oceanus ?? 0));
  const spreadMode = maxDelta / totalGrowth >= 0.45 ? "Explosive" : "Gradual";
  const overlapValues = rows.map((row) => Math.min(row.oceanus, row.compare));
  const maxOverlap = Math.max(0, ...overlapValues);
  const maxOverlapIndex = maxOverlap > 0 ? overlapValues.indexOf(maxOverlap) : Math.max(0, rows.findIndex((row) => row.oceanus > 0 && row.compare > 0));
  const fusionStart = Math.max(0, maxOverlapIndex - 1);
  const fusionEnd = Math.min(rows.length - 1, maxOverlapIndex + 1);
  const fusionWindowTop = toY(maxOverlap || max * 0.3) - 8;
  const fusionWindow = `${toX(fusionStart)},${fusionWindowTop} ${toX(fusionEnd)},${fusionWindowTop} ${toX(fusionEnd)},${top + plotHeight} ${toX(fusionStart)},${top + plotHeight}`;
  const compareLabel = activeCompare?.genre ?? "Compared genre";

  return (
    <div className="chartWrap">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Genre Flow">
        <Grid chart={{ left, right: 18, top, bottom, width, height }} />
        {mode === "fusion" && <polygon key={compareLabel} points={`${compareTop} ${base}`} className="areaIndie" />}
        <polygon points={`${oceanusTop} ${base}`} className="areaOceanus" />
        <polygon points={mode === "oceanus" ? `${toX(Math.max(0, spikeIndex - 1))},${top + 6} ${toX(spikeIndex)},${top + 6} ${toX(spikeIndex)},${top + plotHeight} ${toX(Math.max(0, spikeIndex - 1))},${top + plotHeight}` : fusionWindow} className="fusionBrush" />
        {rows.map((row, index) => (
          <text key={row.year} x={toX(index)} y={218}>
            {index % 2 === 0 ? row.year : ""}
          </text>
        ))}
        {mode === "oceanus" && rows.length > 3 && (
          <path
            key={`${mode}-${compareLabel}`}
            d={`M${toX(Math.max(0, spikeIndex - 1))} ${toY(rows[Math.max(0, spikeIndex - 1)].oceanus)} C ${toX(spikeIndex)} ${toY(max * 0.5)}, ${toX(spikeIndex)} ${toY(max * 0.78)}, ${toX(spikeIndex)} ${toY(rows[spikeIndex].oceanus)}`}
            className="spikeArrow"
          />
        )}
      </svg>
      <div className="legendRow">
        <span><i className="swatch cyan" /> Oceanus Folk</span>
        {mode === "fusion" && <span><i className="swatch pink" /> {compareLabel}</span>}
        <span>
          {mode === "oceanus"
            ? `${spreadMode} spread: max +${maxDelta} around ${spikeYear ?? "-"}`
            : `Carousel ${carouselIndex + 1}/${comparisonSeries.length} · Max overlap: ${rows[maxOverlapIndex]?.year ?? "-"} (${maxOverlap})`}
        </span>
      </div>
    </div>
  );
}

function GenreSankey({ data, startYear }: { data?: GenreFlowPayload; startYear: number }) {
  const nodeNames = new Map((data?.nodes ?? []).map((node) => [node.id, node.name || node.id]));
  const allLinks = (data?.links ?? []).filter((link) => link.value > 0);
  const sourceId = allLinks.find((link) => link.source === "Oceanus Folk" || link.target === "Oceanus Folk")
    ? "Oceanus Folk"
    : (allLinks[0]?.source ?? "Oceanus Folk");
  const connected = allLinks
    .filter((link) => link.source === sourceId || link.target === sourceId)
    .map((link) => ({
      ...link,
      targetGenre: link.source === sourceId ? link.target : link.source,
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 7);

  if (!connected.length) {
    return <div className="panelState">当前时间窗没有 Oceanus Folk 的 style-edge 桑基数据。</div>;
  }

  const width = 520;
  const height = 230;
  const maxValue = Math.max(1, ...connected.map((link) => link.value));
  const sourceHeight = 36 + connected.reduce((sum, link) => sum + link.value, 0) / maxValue * 11;
  const targetGap = connected.length > 1 ? 164 / (connected.length - 1) : 0;

  return (
    <div className="chartWrap">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Genre Sankey">
        <defs>
          {connected.map((link, index) => (
            <linearGradient key={link.targetGenre} id={`sankeyGradient-${index}`} x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="rgba(90, 216, 232, 0.72)" />
              <stop offset="100%" stopColor={sankeyColor(index, 0.74)} />
            </linearGradient>
          ))}
        </defs>
        <g className="sankeyFlow">
          <rect x="42" y={115 - sourceHeight / 2} width="118" height={sourceHeight} rx="10" className="sankeyNode source" />
          <text x="101" y="110" className="sankeyLabel main">{nodeNames.get(sourceId) ?? sourceId}</text>
          <text x="101" y="126" className="sankeyLabel subtle">style edges · {startYear}-2040</text>
          {connected.map((link, index) => {
            const targetY = 32 + index * targetGap;
            const targetHeight = 18 + (link.value / maxValue) * 18;
            const strokeWidth = 5 + (link.value / maxValue) * 21;
            const targetName = nodeNames.get(link.targetGenre) ?? link.targetGenre;
            return (
              <g key={`${link.source}-${link.target}-${index}`} className={`sankeyGroup sankeyGroup${index}`}>
                <path
                  d={`M160 115 C 244 115, 290 ${targetY}, 366 ${targetY}`}
                  className="sankeyLink"
                  style={{ strokeWidth, stroke: `url(#sankeyGradient-${index})`, animationDelay: `${index * 90}ms` }}
                />
                <rect x="366" y={targetY - targetHeight / 2} width="116" height={targetHeight} rx="8" className="sankeyNode target" />
                <text x="424" y={targetY - 2} className="sankeyLabel main">{targetName}</text>
                <text x="424" y={targetY + 11} className="sankeyLabel subtle">value {link.value}</text>
              </g>
            );
          })}
        </g>
      </svg>
      <div className="legendRow">
        <span><i className="swatch cyan" /> {nodeNames.get(sourceId) ?? sourceId}</span>
        {connected.slice(0, 4).map((link, index) => (
          <span key={link.targetGenre}><i className={`swatch sankeySwatch${index}`} /> {nodeNames.get(link.targetGenre) ?? link.targetGenre}</span>
        ))}
        <span>Sankey · style_edges · {connected.length} flows</span>
      </div>
    </div>
  );
}

function sankeyColor(index: number, alpha: number) {
  const colors = [
    `rgba(245, 140, 184, ${alpha})`,
    `rgba(240, 179, 95, ${alpha})`,
    `rgba(114, 198, 143, ${alpha})`,
    `rgba(185, 155, 245, ${alpha})`,
    `rgba(120, 170, 255, ${alpha})`,
    `rgba(90, 216, 232, ${alpha})`,
    `rgba(248, 226, 189, ${alpha})`,
  ];
  return colors[index % colors.length];
}

function StarProfiler({
  profiles,
  rising,
  focusCandidateId,
  settled = false,
}: {
  profiles?: PersonProfilePayload;
  rising?: RisingStarsPayload;
  focusCandidateId?: string;
  settled?: boolean;
}) {
  const anchor = profiles?.profiles[0];
  const candidates = profiles?.profiles.slice(1) ?? [];
  if (!anchor || !candidates.length || !rising?.candidates.length) {
    return <div className="panelState">没有足够的画像或候选新星数据。</div>;
  }

  const dimensions = profiles.dimensions.slice(0, 5);
  const selectedCandidate = candidates.find((candidate) => candidate.person_id === focusCandidateId) ?? candidates[0];
  const selectedRising = rising.candidates.find((candidate) => candidate.person_id === selectedCandidate.person_id) ?? rising.candidates[0];
  const size = 230;
  const center = size / 2;
  const radius = 76;
  const axes = dimensions.map((dimension, index) => {
    const angle = -Math.PI / 2 + (index * Math.PI * 2) / dimensions.length;
    const sailor = Math.min(1.25, Number(anchor.metrics[dimension] ?? 0));
    const rookie = Math.min(1.25, Number(selectedCandidate.metrics[dimension] ?? 0));
    return {
      label: dimLabel(dimension),
      sailor,
      rookie,
      x: center + Math.cos(angle) * radius,
      y: center + Math.sin(angle) * radius,
      angle,
    };
  });
  const polygonFor = (key: "sailor" | "rookie") =>
    axes
      .map((axis) => {
        const valueRadius = (axis[key] / 1.25) * radius;
        return `${center + Math.cos(axis.angle) * valueRadius},${center + Math.sin(axis.angle) * valueRadius}`;
      })
      .join(" ");

  return (
    <div className="profilerLayout">
      <svg key={`profile-${selectedCandidate.person_id}`} viewBox={`0 0 ${size} ${size}`} role="img" aria-label="Star Profiler">
        {[0.35, 0.7, 1].map((scale) => (
          <polygon
            key={scale}
            points={axes.map((axis) => `${center + Math.cos(axis.angle) * radius * scale},${center + Math.sin(axis.angle) * radius * scale}`).join(" ")}
            className="radarRing"
          />
        ))}
        {axes.map((axis) => (
          <g key={axis.label}>
            <line x1={center} y1={center} x2={axis.x} y2={axis.y} className="radarAxis" />
            <text x={axis.x} y={axis.y}>{axis.label}</text>
          </g>
        ))}
        <polygon points={polygonFor("sailor")} className="radarSailor" />
        <polygon points={polygonFor("rookie")} className="radarRookie" />
      </svg>
      <div className="rankList">
        <div className={settled ? "candidateSpotlight settled" : "candidateSpotlight"}>
          <span>{settled ? "Final closest match" : "Comparing candidate"}</span>
          <strong>{selectedCandidate.name}</strong>
          <b>{selectedRising?.score ?? "-"}</b>
        </div>
        {rising.candidates.slice(0, TASK3_CANDIDATE_COUNT).map((star, index) => (
          <div
            key={star.name}
            className={star.person_id === selectedCandidate.person_id ? "rankItem active" : "rankItem"}
            style={{ animationDelay: `${720 + index * 70}ms` }}
          >
            <span>{index + 1}</span>
            <div>
              <strong>{star.name}</strong>
              <p>{star.reason}</p>
            </div>
            <b>{star.score}</b>
          </div>
        ))}
      </div>
    </div>
  );
}

function dimLabel(dimension: string) {
  const labels: Record<string, string> = {
    song_count: "Output",
    notable_rate: "Notable",
    active_years: "Active",
    unique_collaborators: "Collab",
    genre_entropy: "Genre Mix",
    degree: "Degree",
    pagerank: "PageRank",
  };
  return labels[dimension] ?? dimension;
}
