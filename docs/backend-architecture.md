# 后端与数据层说明（FastAPI + Neo4j）

栈：**FastAPI** 提供 HTTP API；**Neo4j** 存储图与属性；复杂聚合在 **Cypher** 中完成，必要时对高度重复指标做**预计算**写入节点属性。

---

## 一、接口层职责

- 将前端 Panel 的需求拆成**资源化的只读接口**（第一期以查询为主）。
- **校验**查询参数（年份范围、limit、允许的 relation 类型枚举）。
- **限流与超时**：避免单次返回过大子图拖垮浏览器与数据库。
- **统一响应信封**（建议）：`{ data, meta }`，`meta` 可含 `truncated`、`total_hint`、`evidence_id`。

---

## 二、核心 API 设计（与 Panel 对齐）

以下为推荐路径与语义；具体字段可在 OpenAPI 中固化。

### 2.1 `POST /api/v1/graph/subgraph`

**用途**：Influence Galaxy 初始画布。

**请求体（示例）**

```json
{
  "start_year": 2020,
  "end_year": 2030,
  "genres": ["Oceanus Folk", "Indie Pop"],
  "seed_person_ids": [123],
  "rel_types": ["IN_STYLE_OF", "PERFORMER_OF"],
  "limit_nodes": 800,
  "only_notable_songs": false
}
```

**响应（示例）**

```json
{
  "data": {
    "nodes": [{ "id": "...", "label": "Person", "name": "...", "props": {} }],
    "links": [{ "source": "...", "target": "...", "type": "IN_STYLE_OF", "props": {} }]
  },
  "meta": { "truncated": false, "node_count": 120, "link_count": 340 }
}
```

**说明**

- `seed_person_ids` 可选：有则做 **k-hop 子图** 或 **可变半径** 采样；无则按时间+流派采样代表性子图（策略需在实现时固定并写进 README）。
- 边方向与多关系图（multigraph）需与 JSON 源数据一致。

---

### 2.2 `GET /api/v1/graph/expand/{node_id}`

**用途**：Galaxy 点击后增量拉邻居。

**查询参数（示例）**

- `rel_types`：逗号分隔
- `direction`：`out` | `in` | `both`
- `limit`：默认 200

**响应**：与 `subgraph` 相同的 `nodes`/`links` 增量集合（前端合并去重）。

---

### 2.3 `GET /api/v1/analysis/career-track`

**用途**：Panel A — Career Arc。

**查询参数**

- `person_id`（推荐）或 `person_name`（需唯一索引支持）
- `start_year`, `end_year`

**响应（示例）**

```json
{
  "data": {
    "person": { "id": "...", "name": "Sailor Shift" },
    "by_year": [
      { "year": 2028, "song_count": 5, "notable_count": 3, "genres": ["Oceanus Folk"] }
    ],
    "works": [
      {
        "song_id": "...",
        "title": "...",
        "release_date": "2028-05-01",
        "notable": true,
        "genre": "Oceanus Folk"
      }
    ]
  },
  "meta": {}
}
```

**说明**

- `by_year` 支撑趋势图；`works` 支撑甘特式细条（可按 release_date 排序）。
- `notoriety_date` 若存在于数据源，可一并返回用于「成名耗时」辅助叙事。

---

### 2.4 `GET /api/v1/analysis/genre-flow`

**用途**：Panel C — Genre Flow（桑基 / 河流图）。

**查询参数**

- `start_year`, `end_year`
- `metric`：`style_edges` | `song_cowrite` | `genre_mix`（具体实现选一种主指标，其余可二期）
- `source_genre`：可选，聚焦 Oceanus Folk 等

**响应（桑基，示例）**

```json
{
  "data": {
    "nodes": [{ "id": "Oceanus Folk" }, { "id": "Indie Pop" }],
    "links": [{ "source": "Oceanus Folk", "target": "Indie Pop", "value": 45 }]
  },
  "meta": {}
}
```

**响应（河流图，示例）**

```json
{
  "data": {
    "series": [
      { "genre": "Oceanus Folk", "points": [{ "year": 2025, "value": 12 }, ...] }
    ]
  },
  "meta": {}
}
```

**说明**

- 业务定义要明确：例如「桑基的 value = 时间窗内 IN_STYLE_OF 从 A 流派艺人到 B 流派艺人的边数」——避免前后端对「渗透」理解不一致。

---

### 2.5 `GET /api/v1/analysis/person-profile`

**用途**：Panel D — Star Profiler。

**查询参数**

- `person_ids`：重复多次或逗号分隔
- `start_year`, `end_year`

**响应（示例）**

```json
{
  "data": {
    "profiles": [
      {
        "person_id": "...",
        "name": "...",
        "metrics": {
          "song_count": 40,
          "notable_rate": 0.15,
          "active_years": 8,
          "unique_collaborators": 22,
          "genre_entropy": 1.2,
          "degree": 30,
          "pagerank": 0.004
        }
      }
    ],
    "dimensions": ["song_count", "notable_rate", "..."]
  },
  "meta": {}
}
```

**说明**

- 雷达图需前端对 `metrics` 做 **min-max 或分位数归一化**；后端可提供 `metrics_normalized` 简化前端。

---

### 2.6 `GET /api/v1/search`

**用途**：全局搜索 Person / Song。

**查询参数**：`q`, `type`（person|song|all）, `limit`

**响应**：候选列表，含 `id`、`label`、`subtitle`（如代表作年份）。

---

## 三、数据层：Neo4j 如何建模与支持查询

### 3.1 节点与关系（与 MC1 数据对齐的方向）

**节点标签（示例）**

- `Person`, `Song`, `RecordLabel`, `MusicalGroup`, `Album`（以实际导入为准）

**关键属性**

- `Song`：`release_date`, `genre`, `notable`, `single`, `name`
- `Person`：`name`；若有 `stage_name` 需合并策略

**关系类型（示例）**

- `PERFORMER_OF`（Person→Song）
- `IN_STYLE_OF`（风格影响，方向需与叙事「谁影响谁」一致）
- `MEMBER_OF`, `SIGNED_TO` 等（按源数据 12 类关系完整导入）

导入时保留源数据中的 **数值 `id`** 或生成稳定 `id` 字符串，与 API 中 `node_id` 一致。

---

### 3.2 索引与约束

- **唯一性**：`Person(id)` 或 `Person(name)`（若全局唯一）用约束。
- **查找**：`Song(release_date)`、`Song(notable)`、`Song(genre)` 复合场景可拆为多索引。
- **全文**：对 `Person.name`、`Song.name` 建全文索引以支持 `/search`。

---

### 3.3 预计算（可选，提升 Profiler 与子图体验）

在批处理或导入后执行：

- `Person.song_count`, `Person.notable_song_count`（可限定全时期或滚动窗口由你定义）
- `Person.degree` / `Person.pagerank`（需在子图定义一致的前提下说明是「全局」还是「年度子图」）
- `Song.fame_gap`：若存在 `notoriety_date`，则 `fame_gap = notoriety_date - release_date`

**注意**：预计算若带时间窗，应明确是「全历史」还是「接口传入窗口」；窗口敏感指标建议**运行时 Cypher 聚合**，避免组合爆炸。

---

### 3.4 典型 Cypher 思路（非最终实现）

- **Career track**：`MATCH (p:Person)-[:PERFORMER_OF]->(s:Song) WHERE id(p)=$pid AND s.release_date IN range` → `WITH substring(s.release_date,0,4) AS year` 聚合。
- **Genre sankey**：在时间窗内 `MATCH (s1:Song)-[:IN_STYLE_OF]->(p:Person)<-[:IN_STYLE_OF]-(s2:Song)` 或直接使用「流派→流派」聚合规则（以实现时选定的语义为准）。
- **Subgraph**：`CALL apoc.path.subgraphAll`（若使用 APOC）或限定 `LIMIT` 的 `MATCH` 模式。

---

## 四、数据交互总览（后端视角）

```
[React Store: yearRange, genres, focusedPersonId, ...]
        │  query params / JSON body
        ▼
[FastAPI: 校验 → Neo4j Driver → Cypher]
        │
        ▼
[JSON: nodes/links 或 表格型聚合]
        │
        ▼
[React Panel: 图表渲染与联动]
```

---

## 五、非功能与运维

- **连接**：Neo4j Driver 使用连接池；FastAPI 生命周期内创建/关闭 driver。
- **安全**：生产环境禁止默认密码；CORS 白名单仅前端域名。
- **可追溯**：对复杂分析响应可写入 `evidence_id`（如查询模板 id + 参数 hash），便于二期叙事引用。

---

## 六、Panel ↔ API 速查（后端实现清单）

| Panel | 主要端点 |
|-------|----------|
| Career Arc | `GET /analysis/career-track` |
| Influence Galaxy | `POST /graph/subgraph`, `GET /graph/expand/{node_id}` |
| Genre Flow | `GET /analysis/genre-flow` |
| Star Profiler | `GET /analysis/person-profile` |
| 全局搜索 | `GET /search` |
