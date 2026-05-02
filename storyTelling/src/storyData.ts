export type PanelKey = "career" | "galaxy" | "genre" | "profiler";

export type Act = {
  id: number;
  kicker: string;
  title: string;
  subtitle: string;
  objective: string;
  voiceover: string;
  actions: string[];
  activePanels: PanelKey[];
  insight: string;
};

export const acts: Act[] = [
  {
    id: 1,
    kicker: "Act I / 巨星的崛起",
    title: "Profile Sailor Shift",
    subtitle: "从 Career Arc 出发，追踪 Sailor Shift 从首发作品到 Notable 爆发期的职业弧线。",
    objective: "聚焦 Sailor Shift，读取她发片频率、成名节点与 Ivy Echoes 背后的关系伏笔。",
    voiceover:
      "我们首先看 Sailor Shift 的职业时轴。早期作品保持稳定输出，随后 Notable 标签在爆发年份集中出现，说明她不是突然走红，而是在一段酝酿期后完成跃迁。",
    actions: [
      "全局搜索锁定 Sailor Shift",
      "在 Career Arc 中高亮出道到爆发年份",
      "保留 Ivy Echoes 成员作为后续网络线索",
    ],
    activePanels: ["career", "galaxy"],
    insight: "Sailor Shift 的增长像一条蓄势曲线：作品频率先稳定，Notable 声量随后集中放大。",
  },
  {
    id: 2,
    kicker: "Act II / 流派的扩散",
    title: "Map Oceanus Folk",
    subtitle: "把视角从个人放大到生态，观察 Oceanus Folk 是否爆炸式增长，并如何流入 Indie Pop。",
    objective: "用 Genre Flow 判断传播节奏，再用 Influence Galaxy 找到跨流派桥梁节点。",
    voiceover:
      "Oceanus Folk 的面积在关键年份陡峭增厚，呈现典型爆发式增长。随后它与 Indie Pop 发生交汇，网络中的桥梁艺人把宏观趋势落实为具体的合作关系。",
    actions: [
      "切换全局流派筛选为 Oceanus Folk + Indie Pop",
      "在 Genre Flow 中框选融合年份",
      "回到 Influence Galaxy 查看 Bridge Nodes",
    ],
    activePanels: ["genre", "galaxy"],
    insight: "Oceanus Folk 的破圈不是单点传播，而是由跨流派合作者接力完成的网络扩散。",
  },
  {
    id: 3,
    kicker: "Act III / 明日之星",
    title: "Predict Rising Stars",
    subtitle: "将巨星模型应用到新人候选，结合 Star Profiler 与 Career Arc 公布三位 Rising Stars。",
    objective: "提取巨星成名前的共同特征，验证新人是否处于类似的爆发前夜。",
    voiceover:
      "我们把 Sailor Shift 的早期特征抽象成巨星模型：高产、跨界合作、网络中心度和流派吸附能力。三位新人画像与这个模型高度贴合，并且职业曲线正在进入上升前夜。",
    actions: [
      "在 Star Profiler 叠加 Sailor Shift 与候选新人",
      "对比候选人的早期 Career Arc 斜率",
      "公布三位最接近巨星模型的 Rising Stars",
    ],
    activePanels: ["profiler", "career", "galaxy"],
    insight: "预测不是主观推荐，而是由画像相似度、网络密度和时序斜率共同支撑。",
  },
];

export const careerSeries = [
  { year: 2014, songs: 1, notable: 0 },
  { year: 2015, songs: 2, notable: 0 },
  { year: 2016, songs: 2, notable: 1 },
  { year: 2017, songs: 4, notable: 1 },
  { year: 2018, songs: 5, notable: 2 },
  { year: 2019, songs: 7, notable: 5 },
  { year: 2020, songs: 8, notable: 6 },
  { year: 2021, songs: 9, notable: 7 },
  { year: 2022, songs: 8, notable: 6 },
];

export const rookieSeries = [
  { name: "Luna Reef", values: [0, 1, 2, 4, 6] },
  { name: "Niko Vale", values: [1, 1, 3, 4, 7] },
  { name: "Mira Tide", values: [0, 2, 2, 5, 8] },
];

export const genreFlow = [
  { year: 2016, oceanus: 6, indie: 18 },
  { year: 2017, oceanus: 8, indie: 20 },
  { year: 2018, oceanus: 15, indie: 23 },
  { year: 2019, oceanus: 34, indie: 29 },
  { year: 2020, oceanus: 48, indie: 38 },
  { year: 2021, oceanus: 55, indie: 44 },
  { year: 2022, oceanus: 52, indie: 50 },
];

export const galaxyNodes = [
  { id: "sailor", label: "Sailor Shift", x: 50, y: 48, group: "focus" },
  { id: "ivy", label: "Ivy Echoes", x: 28, y: 38, group: "band" },
  { id: "maya", label: "Maya", x: 20, y: 58, group: "member" },
  { id: "lila", label: "Lila", x: 36, y: 68, group: "member" },
  { id: "oceanus", label: "Oceanus Folk", x: 68, y: 32, group: "genre" },
  { id: "indie", label: "Indie Pop", x: 77, y: 56, group: "genre" },
  { id: "bridge", label: "Bridge Nodes", x: 63, y: 70, group: "bridge" },
];

export const galaxyLinks = [
  ["ivy", "sailor", "MEMBER_OF"],
  ["maya", "ivy", "MEMBER_OF"],
  ["lila", "ivy", "MEMBER_OF"],
  ["oceanus", "sailor", "IN_STYLE_OF"],
  ["oceanus", "bridge", "PERFORMER_OF"],
  ["bridge", "indie", "IN_STYLE_OF"],
  ["bridge", "sailor", "COLLAB"],
];

export const profilerMetrics = [
  { label: "Output", sailor: 88, rookie: 82 },
  { label: "Notable", sailor: 92, rookie: 76 },
  { label: "Network", sailor: 86, rookie: 84 },
  { label: "Genre Mix", sailor: 78, rookie: 81 },
  { label: "Fame Gap", sailor: 72, rookie: 69 },
];

export const risingStars = [
  { name: "Luna Reef", score: 91, reason: "高产且频繁连接 Oceanus Folk 与 Indie Pop" },
  { name: "Niko Vale", score: 88, reason: "合作网络快速变密，桥梁节点得分高" },
  { name: "Mira Tide", score: 86, reason: "职业曲线斜率接近 Sailor Shift 爆发前夜" },
];
