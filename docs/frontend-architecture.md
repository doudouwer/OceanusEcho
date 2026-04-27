# 前端架构说明（业务层 + 底层能力）

栈：**React**。与后端通过 **FastAPI** 暴露的 REST API 通信；可视化可选用 **ECharts**、**D3**、**react-force-graph** 等，以「同一套全局状态」驱动多图联动。

---

## 一、布局：多视图联动（Linked Multiple Views）

### 1.1 建议布局

- **全局条（Global Chrome）**：时间范围（如 2023–2040）、流派多选、搜索框、当前聚焦艺人展示与清除。
- **主工作区**：四个 Panel 占位明确（四宫格或「1 大 + 3 小」），每个 Panel 有标题、简短说明、加载与空状态。
- **联动原则**：任何全局筛选变化 → 所有 Panel **要么重新请求，要么用已拉取数据在客户端过滤**（需在实现上统一策略，见下文）。

### 1.2 全局状态（当前实现 + 预留字段）

| 字段 | 含义 | 典型驱动方 |
|------|------|------------|
| `yearRange` | `[start, end]` | 时间 Slider |
| `selectedGenres` | 流派 id 或名称列表 | 多选框 |
| `focusedPersonId` | 当前故事主角 | Galaxy 点击、搜索选中 |
| `comparePersonIds` | 对比用 2–3 人 | Profiler 多选 |
| `focusedTimeRange` | 细时间窗（预留） | 目前主要由 Galaxy 读取；Career 尚未写入 |
| `highlightSongIds` | 高亮歌曲（预留） | 当前 UI 暂未消费 |

实现可选用 **Zustand** 或 **Redux Toolkit**；关键是**序列化查询参数**与 API 对齐，便于缓存。

---

## 二、前端业务层：每个 Panel 做什么

### Panel A — 职业时轴 (Career Arc)

**业务目标**

- 展示指定艺人（默认 `focusedPersonId`，无则提示搜索）在时间上的**作品产出节奏**。
- 区分**普通作品**与 **notable（成名/关键）作品**的分布，支撑「成名速度」「拐点年」叙事。
- 可选：同图叠加**累计作品数、累计 notable 数**等多条折线，形成「多线趋势图」。

**图表形态（当前）**

- 按年聚合 `song_count`、`notable_count` 的双折线（含面积填充）+ dataZoom。
- 甘特式作品条带属于后续可扩展项，当前未实现。

**交互（当前）**

- 由全局 `focusedPersonId` + `yearRange` 触发请求并重绘。
- 暂未把 ECharts 的 brush/dataZoom 事件写回 store；`focusedTimeRange` 的写入仍是预留能力。

**数据交互**

- 初次进入 / `focusedPersonId` 或 `yearRange` 变化：请求 `GET /api/v1/analysis/career-track`（参数见后端文档）。

---

### Panel B — 影响力网络 (Influence Galaxy)

**业务目标**

- 展示**风格影响**（如 IN_STYLE_OF 指向/来自）、**表演关系**（PERFORMER_OF）、**成员/厂牌**等子集构成的子图。
- 支持**钻取**：从种子节点展开邻居，避免一次加载全图。

**图表形态（当前）**

- 力导向图：节点覆盖 `Person` / `MusicalGroup` / `Song` / `Album` / `RecordLabel`。
- 颜色按节点类别与 `cluster_id`（社区）着色；连线按关系类型着色。

**交互（当前）**

- 点击 `Person` / `MusicalGroup`：更新 `focusedPersonId` 并调用 expand 增量展开。
- 对已展开节点做去重，避免重复扩展。
- `focusedTimeRange` 若已存在会优先覆盖 `yearRange` 发起请求；Career 面板当前尚未产出该值。

**数据交互**

- 初始化：`POST /api/v1/graph/subgraph`（带 `yearRange`、`genres`、节点上限等）。
- 展开：`GET /api/v1/graph/expand/{node_id}`（可选 `rel_types`、`direction`、`limit`）。

---

### Panel C — 流派演变 (Genre Flow)

**业务目标**

- 回答「Oceanus Folk 如何**流向** Indie Pop」：用**桑基**表达源流派 → 目标流派的**强度**（由共现、风格继承边、或歌曲级转移统计定义，以后端为准）。
- 用 **Streamgraph** 可看各流派**随时间的堆叠占比**（与桑基二选一或页内 Tab 切换）。

**图表形态**

- **桑基**：nodes = 流派；links = `{ source, target, value }`。
- **河流图**：横轴时间，纵轴为各流派作品量或「风格边权重」的堆叠曲线。

**交互**

- 时间范围变化 → **重新请求**聚合结果（流派流量对年份敏感）。
- 点击某一链路 → 可选：过滤 Galaxy 只显示相关流派或打开明细列表。

**数据交互（当前）**

- `GET /api/v1/analysis/genre-flow`，`metric` 仅使用 `style_edges` 与 `genre_mix` 两种。

---

### Panel D — 艺人画像 (Star Profiler)

**业务目标**

- 选 **2–3 名艺人**，对比多维指标：如**作品数、notable 率、活跃年数、合作者数、流派广度、图中心性（若后端提供）**等。
- 支撑「谁更像正在上升的新星」：**用可解释指标呈现**；若二期接模型，雷达图可叠加「预测分」维度。

**图表形态**

- **雷达图**：每人一条线，维度为统一量纲后的指标（0–1 或分位数）。
- **属性矩阵**：行 = 艺人，列 = 指标，单元格可着色。

**交互**

- 从顶部 Ivy Echoes 快捷按钮或搜索结果添加对比人 → 更新 `comparePersonIds`。
- 切换全局 `yearRange` → 指标应基于**同一时间窗**重算（请求或缓存失效）。

**数据交互（当前）**

- `GET /api/v1/analysis/person-profile`：使用逗号分隔参数 `person_ids=17255,17256`。
- 默认 `normalized=true`，以第一个人作为锚点输出归一化雷达维度。

---

## 三、前端底层：React 提供的公共能力

### 3.1 API 客户端

- 封装 `fetch` 或 `axios`：**baseURL**、超时、错误结构统一解析。
- **查询键**：由 `yearRange`、`genres`、`personId` 等稳定序列化，配合 **TanStack Query (React Query)** 做缓存、去重、后台刷新（推荐）。

### 3.2 图表与性能

- **Graph Hook**：封装力导向的 `data` 合并、去重、`nodeId` 规范、暂停仿真等。
- **降级策略**：子图节点数超过阈值时切换 **聚合视图** 或提示缩小时间范围（与后端 `limit` 配合）。

### 3.3 设计系统（轻量即可）

- 统一 **色板**（流派色、notable 高亮、中性灰）、**字号**、**Panel 卡片样式**，保证四图并排时视觉一致。

### 3.4 可选：叙事锚点（二期）

- 各 Panel 将「关键发现」以结构化对象推入 `narrativeAnchors`（如 `{ type, year, personId, summary }`），便于后续 Agent 消费。

---

## 四、前端视角：Panel ↔ API ↔ 全局状态（速查）

| Panel | 主要 API | 依赖全局状态 |
|-------|----------|----------------|
| Career Arc | `career-track` | `focusedPersonId`, `yearRange` |
| Influence Galaxy | `subgraph`, `expand` | `yearRange`, `selectedGenres`, `focusedPersonId`, `focusedTimeRange`（若存在） |
| Genre Flow | `genre-flow` | `yearRange`, `selectedGenres` |
| Star Profiler | `person-profile` | `comparePersonIds`, `yearRange` |
| 全局搜索 | `search` | 写入 `focusedPersonId` 或 `comparePersonIds` |

---

## 五、与后端联调的约定要点

- 所有带年份的接口使用**同一闭区间语义**：`start_year`、`end_year` 包含端点。
- 列表类返回统一 **分页或硬上限**，前端需处理 `truncated: true` 之类标志（若后端提供）。
- **节点 id** 当前约定为 `original_id` 字符串；仅在缺失时回退 `elementId`。前端按字符串处理并避免假设数值类型。
