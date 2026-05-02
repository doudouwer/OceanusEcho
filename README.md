# OceanusEcho

**MSBD5005 ·** 项目架构说明（Neo4j + FastAPI + React）

面向「多视图联动（Linked Multiple Views）」的音乐产业图谱可视化：全局时间切片 + 四个核心 Panel 共享同一套筛选与聚焦状态，分别从**时间轴、关系网络、流派流动、艺人画像**四个角度回答记者叙事问题。

详细规格见：

- [前端架构与业务说明](docs/frontend-architecture.md)
- [后端接口与数据层说明](docs/backend-architecture.md)

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 数据层 | Neo4j（图查询 + 可选预计算属性） |
| 接口层 | FastAPI（参数化查询、分页与限流、错误与缓存策略） |
| 前端底层 | React、状态管理（如 Zustand）、图表库（ECharts / D3 / react-force-graph 等） |
| 前端业务 | 各 Panel 容器组件 + 联动逻辑 |

### 前端工程（`frontend/`）

- **栈**：Vite 5、React 18、TypeScript、Zustand、TanStack Query、ECharts、`react-force-graph-2d`。
- **开发**：`cd frontend && npm install && npm run dev`，默认 <http://localhost:5173>；`/api` 已代理到 `http://127.0.0.1:8000`（后端就绪后可直接联调）。
- **数据模式**：当前默认就是在线模式，不再维护前端离线占位图 fallback。前端所有 Panel 直接请求 `/api/v1`。

### 后端工程（`backend/`）

- **栈**：FastAPI、Neo4j Python Driver（异步）、Pydantic Settings。
- **启动**：`cd backend && python3 -m venv .venv && source .venv/bin/activate`（Windows 用 `.venv\Scripts\activate`），`pip install -r requirements.txt`，再执行  
  `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`。
- **环境变量**：复制 `backend/.env.example` 为 `backend/.env`，填写 `NEO4J_PASSWORD`。后端采用在线严格模式：启动时会等待 Neo4j，若不可达则启动失败；运行中健康检查会返回 `503`。
- **OpenAPI**：启动后访问 <http://127.0.0.1:8000/docs>。
- **图模型约定**：Cypher 按 MC1 导入后的标签 `Person` / `Song` 与关系 `PerformerOf`、`InStyleOf` 编写（与 `MC1_graph.json` 中 `Node Type` / `Edge Type` 一致）。若导入脚本使用不同命名，请改 `app/constants.py` 或查询语句。

---

## 四层职责总览

| 层 | 职责 | 产出物 |
|----|------|--------|
| **1. 前端业务层** | 每个 Panel 讲什么故事、用户怎么操作、如何与其他视图联动 | Panel 组件、交互流程、叙事用例 |
| **2. 前端底层** | 跨 Panel 的公共能力：全局状态、请求封装、大图性能、主题与布局 | Store、Hooks、API 客户端、设计系统 |
| **3. 后端接口层** | 把业务问题翻译成稳定、可缓存、可限流的 HTTP API | REST（或少量 RPC）路由、DTO、校验 |
| **4. 数据层** | 图模型、索引、聚合字段、复杂分析用 Cypher / 预计算 | Neo4j 约束与索引、导入脚本、可选批处理任务 |

---

## 四个核心可视化模块（与业务问题对应）

布局建议：**顶部或左侧为全局控制器（时间范围、流派、搜索）**；主区域四宫格或「一大三小」突出当前叙事重点，所有图订阅同一全局状态。

| 模块 | 可视化形式 | 要解决的业务问题 | 主要数据对象 |
|------|------------|------------------|--------------|
| **A. 职业时轴 (Career Arc)** | 增强甘特图 / 多线趋势图 | Sailor 等人**发片频率**、**成名速度**（如 notable 时间相对首发）、**成名作**在时间上的分布 | Person、Song（release_date、notable、genre） |
| **B. 影响力网络 (Influence Galaxy)** | 力导向图 | **谁影响了她**（风格溯源）、**协作关系**（同歌、同厂牌、同组合等）、**社区结构**（簇、桥梁节点） | Person、Song、关系 IN_STYLE_OF、PERFORMER_OF、MEMBER_OF 等 |
| **C. 流派演变 (Genre Flow)** | 桑基图 / 河流图（Streamgraph） | Oceanus Folk 等标签如何随时间**渗透、混合**到 Indie Pop 等（边、共现、风格继承的宏观流量） | Song.genre、风格关系、时间切片下的聚合 |
| **D. 艺人画像 (Star Profiler)** | 雷达图 / 属性矩阵 | **多艺人对比**（产出、连接度、成名密度、流派广度等）、支撑「谁像未来的新星」的**可解释指标**（非必须一期上模型） | Person + 预计算或实时聚合特征 |

---

## 多视图联动：数据怎么「流」

1. **单一事实来源**：用户调整「年份区间、选中艺人、流派白名单」时，只更新**全局 Store**（前端底层）。
2. **各 Panel 响应**：订阅 Store；需要时调用对应 API（带相同查询参数），避免各组件私自维护不一致的筛选条件。
3. **聚焦与刷选（Brush）**：例如在 Career Arc 上框选一段时间 → 写入 `focusedTimeRange`；Influence Galaxy 仅高亮该时段内活跃节点或按需调用 `subgraph` 缩小范围。
4. **节点点击**：在 Galaxy 点击某人 → 写入 `focusedPersonId`；Career Arc / Genre Flow / Profiler 以该人为默认主角或对比轴之一。
5. **后端一致性**：同一套查询参数（`start_year`、`end_year`、`genres` 等）在多个接口中语义一致，便于前端缓存键设计与联调。

更细的请求/响应字段与场景 walkthrough 见前后端两份文档。

---

## 仓库内数据说明

原始图数据可参考 `MC1_release/MC1_graph.json`（节点含 `Person`、`Song`、`RecordLabel` 等；Song 含 `release_date`、`genre`、`notable` 等）。导入 Neo4j 时需在数据层文档中固定**标签、关系类型与属性命名**，与 API 字段一一对应。

---

## 非功能要求（摘要）

- **规模**：节点数量大时需子图加载、邻居展开、上限与 Cluster 模式（见前端文档）。
- **可追溯**：关键分析接口可返回 `evidence` 或查询标识，便于后续叙事/Agent 引用（见后端文档）。
- **安全与运维**：API 限流、Neo4j 连接池、环境变量管理生产配置。

---

## 后端启动指南

### 环境要求

- Python 3.9+
- Docker + Docker Compose

### 快速启动

```bash
# 一键启动 Neo4j + 后端（不询问、不卡住；需已打开 Docker Desktop）
./scripts/start.sh

# 首次有 MC1_graph.json 时，一并导入图数据
./scripts/start.sh --import
```

### 手动启动

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动 Neo4j
docker compose up -d neo4j
until docker exec oceanecho-neo4j cypher-shell -u neo4j -p password "RETURN 1;" >/dev/null 2>&1; do
  echo "waiting neo4j bolt ready..."
  sleep 1
done

# 导入数据
python -m scripts.import_data --path ../MC1_release/MC1_graph.json

# 启动 API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 服务地址

- API 文档: http://localhost:8000/docs
- Neo4j Browser: http://localhost:7474
- Neo4j 账号: neo4j / password

### 功能验证与效果预览

在后端与 Neo4j 启动后，可运行：

```bash
cd backend
python -m scripts.test_services
```

该脚本会：
- 验证 `/health`、搜索、Career、Genre、Person Profile 接口是否可用
- 重点验证 `Influence Galaxy` 的 `subgraph + expand` 是否生效
- 输出社区/桥接节点摘要并把完整 JSON 结果写到 `/tmp/oceanusecho-preview/...`
