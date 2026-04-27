# 后端与数据层说明（FastAPI + Neo4j）

栈：**FastAPI** 提供 HTTP API；**Neo4j** 存储图与属性；复杂聚合在 **Cypher** 中完成，必要时对高度重复指标做**预计算**写入节点属性。

当前后端采用在线严格模式：Neo4j 未就绪时服务启动失败（fail fast），`/health` 在连接异常时返回 HTTP `503`。

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
  "max_hops": 2,
  "limit_nodes": 800,
  "only_notable_songs": false
}
```

**响应（示例）**

```json
{
  "data": {
    "graph": {
      "nodes": [
        { "id": "123", "label": "Person", "name": "Sailor Shift", "props": {} },
        { "id": "456", "label": "Song", "name": "Moon Over the Tide", "props": {} }
      ],
      "links": [
        { "source": "123", "target": "456", "type": "PERFORMER_OF", "props": {} }
      ]
    },
    "seed_people": [],
    "clusters": [],
    "bridge_nodes": []
  },
  "meta": { "truncated": false, "node_count": 2, "link_count": 1, "db": "connected" }
}
```

**说明**

- 响应始终包装在 `{ graph: { nodes, links }, seed_people, clusters, bridge_nodes }` 结构中，与前端 `InfluenceGalaxyPayload` 类型对齐。
- `rel_types` 会被严格校验并映射到 Neo4j 关系类型；空数组时默认使用系统允许的全部关系类型。
- `seed_person_ids` 可选：有则先抽取候选图，再按 `max_hops` 对 seed 做 BFS 裁剪。
- 返回会附带 `clusters`（人节点投影后的连通社区）和 `bridge_nodes`（桥接节点评分 Top-N）。
- `label` 取值：`Person`、`MusicalGroup`、`Song`、`Album`、`RecordLabel`，由 `labels[0]` 优先级映射生成。
- 边方向与多关系图（multigraph）需与 JSON 源数据一致。

---

### 2.2 `GET /api/v1/graph/expand/{node_id}`

**用途**：Galaxy 点击后增量拉邻居。

**查询参数（示例）**

- `rel_types`：逗号分隔
- `direction`：`out` | `in` | `both`
- `limit`：默认 200
- `start_year`, `end_year`：可选；若提供则对 Song 节点按年份过滤
- `genres`：可选；逗号分隔，限制 Song.genre
- `only_notable_songs`：可选；仅展开 notable Song 相关关系

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
    "summary": {
      "first_release_year": 2028,
      "first_notable_year": 2028,
      "fame_gap_years": null,
      "peak_year": 2034,
      "active_span_years": 13,
      "total_works": 17
    },
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
- `summary` 包含职业汇总指标：`first_release_year`（首张专辑年份）、`first_notable_year`（首个成名作年份）、`peak_year`（产量最高年份）、`active_span_years`（活跃跨度）、`total_works`（总作品数）。
- `notoriety_date` 若存在于数据源，可一并返回用于「成名耗时」辅助叙事。

---

### 2.4 `GET /api/v1/analysis/genre-flow`

**用途**：Panel C — Genre Flow（桑基 / 河流图）。

**查询参数**

- `start_year`, `end_year`
- `metric`：`style_edges` | `genre_mix`（当前实现）
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

- `person_ids`：逗号分隔（最多 20 个）。**第一个 ID 为锚点艺人**，其他艺人的指标均相对于锚点进行归一化
- `start_year`, `end_year`：可选，限定时间窗口
- `normalized`：布尔值，默认 `true`。开启时以锚点艺人的原始值为分母计算比率；关闭时返回原始值

**响应（normalized=false，简明格式）**

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
          "degree": 45,
          "pagerank": 12.0
        }
      }
    ],
    "dimensions": ["song_count", "notable_rate", "active_years", "unique_collaborators", "genre_entropy", "degree", "pagerank"]
  },
  "meta": {}
}
```

**响应（normalized=true，多艺人对比格式）**

```json
{
  "data": {
    "profiles": [
      {
        "person_id": "17255",
        "name": "Sailor Shift",
        "metrics": { "song_count": 1.0, "notable_rate": 1.0, ... },
        "raw_metrics": { "song_count": 40, "notable_rate": 0.15, ... }
      },
      {
        "person_id": "17256",
        "name": "Maya Jensen",
        "metrics": { "song_count": 0.5, "notable_rate": 0.8, ... },
        "raw_metrics": { "song_count": 20, "notable_rate": 0.12, ... }
      }
    ],
    "anchor_id": "17255",
    "anchor_name": "Sailor Shift",
    "dimensions": ["song_count", "notable_rate", "active_years", "unique_collaborators", "genre_entropy", "degree", "pagerank"],
    "normalization": { "type": "ratio-to-anchor" }
  },
  "meta": {}
}
```

**各维度定义与计算说明**

| 维度 | 定义 | 计算方式 |
|------|------|---------|
| song_count | 时间窗内该艺人参与的歌曲总数 | Cypher 聚合（所有贡献关系） |
| notable_rate | 参与歌曲中 notable 歌曲的比例 | `notable 歌曲数 / 总歌曲数` |
| active_years | 有作品发布的年份去重数量 | 发行年份集合大小 |
| unique_collaborators | 有过合作的独立艺人数量 | 所有关系类型（PERFORMER_OF / COMPOSER_OF / PRODUCER_OF / LYRICIST_OF / IN_STYLE_OF / MEMBER_OF / INTERPOLATES_FROM）下的合作者去重 |
| genre_entropy | 流派分布的香农熵（越高 = 流派越多元） | Python `_entropy()` 函数 |
| degree | 全局图度数（所有关系、所有时间） | 原生 Cypher `count(DISTINCT r)` |
| pagerank | 近似 PageRank：2 跳可达的 Person 节点数 | Cypher 2-hop 聚合 |

**归一化说明**

- `normalized=true` 时：`normalized_value = raw_value / anchor_value`（锚点艺人的该维度原始值）
- 锚点艺人自身所有维度归一化值为 `1.0`
- `> 1.0` 表示超过锚点，`< 1.0` 表示不如锚点
- 若锚点该维度为 0，则归一化值为 `0.0`
- 归一化类型由 `normalization.type` 标识为 `"ratio-to-anchor"`

---

### 2.6 `GET /api/v1/search`

**用途**：全局搜索 Person / Song。

**查询参数**：`q`, `type`（person|song|all）, `limit`

**响应（示例）**

```json
{
  "data": {
    "results": [
      { "id": "123", "label": "Sailor Shift", "type": "person", "subtitle": "Person" },
      { "id": "456", "label": "Moon Over the Tide", "type": "song", "subtitle": "2034 · Oceanus Folk" }
    ],
    "total": 2,
    "query": "Sailor"
  },
  "meta": { "db": "connected" }
}
```

**说明**

- `results` 中每个 `SearchHit` 包含 `id`、`label`、`type`（person|song）、`subtitle`（展示辅助信息如年份和流派）。
- `total` 为本次返回的结果总数，`query` 为搜索关键词。
- 搜索对 `Person.name` 和 `Song.name` 做 `CONTAINS` 模糊匹配（忽略大小写）。

---

## 三、数据层：Neo4j 如何建模与支持查询

### 3.1 节点与关系（与 MC1 数据对齐的方向）

**节点标签（示例）**

- `Person`, `Song`, `RecordLabel`, `MusicalGroup`, `Album`（以实际导入为准）

**关键属性**

- `Song`：`release_date`, `genre`, `notable`, `single`, `name`
- `Person`：`name`；若有 `stage_name` 需合并策略

**关系类型（导入脚本当前映射）**

- `PERFORMER_OF`（Person→Song）
- `IN_STYLE_OF`（风格影响，方向需与叙事「谁影响谁」一致）
- `COMPOSER_OF`、`LYRICIST_OF`、`PRODUCER_OF`、`MEMBER_OF`
- `RECORDED_BY`、`DISTRIBUTED_BY`
- `INTERPOLATES_FROM`、`LYRICAL_REFERENCE_TO`、`COVER_OF`、`DIRECTLY_SAMPLES`

导入时将源数据 `id` 写入 `original_id`。后端 API 节点 `id` 优先返回 `original_id`，仅在缺失时回退到 `elementId`。

---

### 3.2 索引与约束

- **唯一性**：`Person(original_id)`、`Song(original_id)` 用约束。
- **查找**：`Song(release_date)`、`Song(genre)` 复合场景可拆为多索引。
- **全文**：对 `Person.name`、`Song.name` 建全文索引以支持 `/search`。

### 3.3 预计算属性

在数据导入时执行以下预计算：

#### inferred_genre（推断流派）

对于没有直接 `genre` 属性的 Person 和 MusicalGroup，通过关联的歌曲计算推断流派：

```cypher
# Person: 根据其参与的歌曲的流派投票
MATCH (p:Person)
OPTIONAL MATCH (p)-[:PERFORMER_OF|COMPOSER_OF|PRODUCER_OF|LYRICIST_OF]-(s:Song)
WHERE s.genre IS NOT NULL
WITH p, s.genre as genre, count(*) as cnt
ORDER BY p, cnt DESC
SET p.inferred_genre = head(collect(genre))[0]
```

```cypher
# MusicalGroup: 根据其成员的歌曲的流派投票
MATCH (g:MusicalGroup)
OPTIONAL MATCH (g)<-[:MEMBER_OF]-(p:Person)-[:PERFORMER_OF|COMPOSER_OF|PRODUCER_OF|LYRICIST_OF]-(s:Song)
WHERE s.genre IS NOT NULL
WITH g, s.genre as genre, count(*) as cnt
ORDER BY g, cnt DESC
SET g.inferred_genre = head(collect(genre))[0]
```

这样可以支持 `InStyleOf` 关系的 Target 为 Person/MusicalGroup 的情况。

#### 其他预计算指标

- `Person.degree`：图度数（连接数）
- `Person.pagerank`：PageRank 中心性
- 可根据需要扩展

**注意**：预计算若带时间窗，应明确是「全历史」还是「接口传入窗口」；窗口敏感指标建议**运行时 Cypher 聚合**，避免组合爆炸。

### 3.3 预计算（可选，提升 Profiler 与子图体验）

在批处理或导入后执行：

- `Person.song_count`, `Person.notable_song_count`（可限定全时期或滚动窗口由你定义）
- `Person.degree` / `Person.pagerank`（需在子图定义一致的前提下说明是「全局」还是「年度子图」）
- `Song.fame_gap`：若存在 `notoriety_date`，则 `fame_gap = notoriety_date - release_date`

**注意**：预计算若带时间窗，应明确是「全历史」还是「接口传入窗口」；窗口敏感指标建议**运行时 Cypher 聚合**，避免组合爆炸。

---

### 3.4 典型 Cypher 思路（非最终实现）

- **Career track**：`MATCH (p:Person)-[:PERFORMER_OF]->(s:Song) WHERE toString(p.original_id)=$pid AND s.release_date IN range` → `WITH substring(s.release_date,0,4) AS year` 聚合。
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
| Career Arc | `GET /api/v1/analysis/career-track` |
| Influence Galaxy | `POST /api/v1/graph/subgraph`, `GET /api/v1/graph/expand/{node_id}` |
| Genre Flow | `GET /api/v1/analysis/genre-flow` |
| Star Profiler | `GET /api/v1/analysis/person-profile` |
| 全局搜索 | `GET /api/v1/search` |
