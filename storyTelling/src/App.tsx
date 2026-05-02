import { useState, type CSSProperties, type ReactNode } from "react";
import {
  acts,
  careerSeries,
  galaxyLinks,
  galaxyNodes,
  genreFlow,
  profilerMetrics,
  risingStars,
  rookieSeries,
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

export default function App() {
  const [activeActId, setActiveActId] = useState(1);
  const activeAct = acts.find((act) => act.id === activeActId) ?? acts[0];
  const visiblePanels = panelOrder.filter((panelKey) => activeAct.activePanels.includes(panelKey));

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
          <strong>{activeAct.activePanels.map((key) => panelLabels[key]).join(" / ")}</strong>
        </div>
      </header>

      <main className="storyGrid">
        <aside className="storyRail">
          <ActSelector activeActId={activeActId} onSelect={setActiveActId} />
          <Narration act={activeAct} />
        </aside>

        <section key={activeAct.id} className={`dashboardGrid panels-${visiblePanels.length}`}>
          {visiblePanels.map((panelKey, index) => renderPanel(panelKey, activeAct.id, index))}
        </section>
      </main>
    </div>
  );
}

function renderPanel(panelKey: PanelKey, actId: number, index: number) {
  const delayStyle = { animationDelay: `${index * 120}ms` };
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
          <CareerArc actId={actId} />
        </PanelFrame>
      );
    case "galaxy":
      return (
        <PanelFrame
          key={panelKey}
          panelKey="galaxy"
          title="Influence network"
          description="以 Sailor Shift / Ivy Echoes / Bridge Nodes 为核心的关系网络叙事。"
          style={delayStyle}
        >
          <InfluenceGalaxy actId={actId} />
        </PanelFrame>
      );
    case "genre":
      return (
        <PanelFrame
          key={panelKey}
          panelKey="genre"
          title="Genre evolution"
          description="Oceanus Folk 与 Indie Pop 的扩散、交汇和爆发式增长。"
          style={delayStyle}
        >
          <GenreFlow />
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
          <StarProfiler />
        </PanelFrame>
      );
  }
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

function Narration({ act }: { act: Act }) {
  return (
    <article className="narration">
      <p className="eyebrow">{act.kicker}</p>
      <h2>{act.title}</h2>
      <p className="subtitle">{act.subtitle}</p>
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
    <article className="panel" style={style}>
      <header className="panelHead">
        <h3>{title}</h3>
        <span>{panelLabels[panelKey]}</span>
      </header>
      <p className="panelDesc">{description}</p>
      <div className="panelBody">{children}</div>
    </article>
  );
}

function CareerArc({ actId }: { actId: number }) {
  const maxValue = 10;
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
    return `${x},${y}`;
  };

  const songPath = careerSeries.map((item, index) => point(item.songs, index, careerSeries.length)).join(" ");
  const notablePath = careerSeries.map((item, index) => point(item.notable, index, careerSeries.length)).join(" ");
  const showRookies = actId === 3;

  return (
    <div className="chartWrap">
      <svg viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-label="Career Arc">
        <Grid chart={chart} />
        <polyline points={songPath} className="linePrimary" />
        <polyline points={notablePath} className="lineDashed" />
        {careerSeries.map((item, index) => (
          <g key={item.year}>
            <circle
              cx={point(item.songs, index, careerSeries.length).split(",")[0]}
              cy={point(item.songs, index, careerSeries.length).split(",")[1]}
              r={item.year >= 2019 && actId === 1 ? 5.5 : 3.5}
              className={item.year >= 2019 && actId === 1 ? "hotDot" : "dot"}
              style={{ animationDelay: `${520 + index * 70}ms` }}
            />
            {index % 2 === 0 && (
              <text x={chart.left + (plotWidth * index) / (careerSeries.length - 1)} y={218}>
                {item.year}
              </text>
            )}
          </g>
        ))}
        {showRookies &&
          rookieSeries.map((rookie, lineIndex) => (
            <polyline
              key={rookie.name}
              points={rookie.values.map((value, index) => point(value, index + 4, careerSeries.length)).join(" ")}
              className={`rookieLine rookie${lineIndex}`}
              style={{ animationDelay: `${760 + lineIndex * 140}ms` }}
            />
          ))}
        <rect
          x={actId === 1 ? 312 : actId === 3 ? 300 : 0}
          y={28}
          width={actId === 1 || actId === 3 ? 152 : 0}
          height={164}
          className="brush"
        />
      </svg>
      <div className="legendRow">
        <span><i className="swatch cyan" /> Songs</span>
        <span><i className="swatch gold" /> Notable</span>
        {showRookies && <span><i className="swatch green" /> Rising candidates</span>}
      </div>
    </div>
  );
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

function InfluenceGalaxy({ actId }: { actId: number }) {
  const highlightedGroups = actId === 1 ? ["focus"] : actId === 2 ? ["genre", "bridge"] : ["bridge", "focus"];

  return (
    <div className="galaxyWrap">
      <svg viewBox="0 0 100 100" role="img" aria-label="Influence Galaxy">
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2.4" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        {galaxyLinks.map(([source, target, type], index) => {
          const a = galaxyNodes.find((node) => node.id === source);
          const b = galaxyNodes.find((node) => node.id === target);
          if (!a || !b) return null;
          const active = actId === 2 ? type !== "MEMBER_OF" : type === "MEMBER_OF" || source === "bridge" || target === "sailor";
          return (
            <line
              key={`${source}-${target}-${type}`}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              className={active ? "galaxyLink active" : "galaxyLink"}
              style={{ animationDelay: `${index * 110}ms` }}
            />
          );
        })}
        {galaxyNodes.map((node, index) => {
          const active = highlightedGroups.includes(node.group);
          return (
            <g
              key={node.id}
              className={active ? "nodeGroup active" : "nodeGroup"}
              style={{ animationDelay: `${280 + index * 95}ms` }}
            >
              <circle cx={node.x} cy={node.y} r={node.group === "focus" ? 6.5 : 4.8} filter={active ? "url(#glow)" : undefined} />
              <text x={node.x} y={node.y + 9}>{node.label}</text>
            </g>
          );
        })}
      </svg>
      <div className="networkNotes">
        <span>IN_STYLE_OF</span>
        <span>MEMBER_OF</span>
        <span>PERFORMER_OF</span>
      </div>
    </div>
  );
}

function GenreFlow() {
  const width = 520;
  const height = 230;
  const left = 44;
  const bottom = 34;
  const top = 22;
  const plotWidth = width - left - 18;
  const plotHeight = height - top - bottom;
  const max = 70;
  const toX = (index: number) => left + (plotWidth * index) / (genreFlow.length - 1);
  const toY = (value: number) => top + plotHeight - (value / max) * plotHeight;
  const oceanusTop = genreFlow.map((row, index) => `${toX(index)},${toY(row.oceanus)}`).join(" ");
  const indieTop = genreFlow.map((row, index) => `${toX(index)},${toY(row.oceanus + row.indie * 0.55)}`).join(" ");
  const base = genreFlow.map((_, index) => `${toX(index)},${top + plotHeight}`).reverse().join(" ");
  const fusionWindow = `${toX(3)},${top + 6} ${toX(5)},${top + 6} ${toX(5)},${top + plotHeight} ${toX(3)},${top + plotHeight}`;

  return (
    <div className="chartWrap">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Genre Flow">
        <Grid chart={{ left, right: 18, top, bottom, width, height }} />
        <polygon points={`${indieTop} ${base}`} className="areaIndie" />
        <polygon points={`${oceanusTop} ${base}`} className="areaOceanus" />
        <polygon points={fusionWindow} className="fusionBrush" />
        {genreFlow.map((row, index) => (
          <text key={row.year} x={toX(index)} y={218}>
            {index % 2 === 0 ? row.year : ""}
          </text>
        ))}
        <path d={`M${toX(2)} ${toY(15)} C ${toX(3)} ${toY(22)}, ${toX(3)} ${toY(46)}, ${toX(4)} ${toY(48)}`} className="spikeArrow" />
      </svg>
      <div className="legendRow">
        <span><i className="swatch cyan" /> Oceanus Folk</span>
        <span><i className="swatch pink" /> Indie Pop</span>
        <span>Fusion years: 2019-2021</span>
      </div>
    </div>
  );
}

function StarProfiler() {
  const size = 230;
  const center = size / 2;
  const radius = 76;
  const axes = profilerMetrics.map((metric, index) => {
    const angle = -Math.PI / 2 + (index * Math.PI * 2) / profilerMetrics.length;
    return {
      ...metric,
      x: center + Math.cos(angle) * radius,
      y: center + Math.sin(angle) * radius,
      angle,
    };
  });
  const polygonFor = (key: "sailor" | "rookie") =>
    axes
      .map((axis) => {
        const valueRadius = (axis[key] / 100) * radius;
        return `${center + Math.cos(axis.angle) * valueRadius},${center + Math.sin(axis.angle) * valueRadius}`;
      })
      .join(" ");

  return (
    <div className="profilerLayout">
      <svg viewBox={`0 0 ${size} ${size}`} role="img" aria-label="Star Profiler">
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
        {risingStars.map((star, index) => (
          <div key={star.name} className="rankItem" style={{ animationDelay: `${720 + index * 120}ms` }}>
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
