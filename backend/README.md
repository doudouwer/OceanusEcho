# OceanusEcho 后端

后端 API 服务，基于 FastAPI + Neo4j 构建，用于音乐知识图谱分析。

## 技术栈

| 组件 | 技术 |
|------|------|
| API 框架 | FastAPI 0.109.0 |
| 数据库 | Neo4j 5.14.0 |
| Python | 3.9+ |

## 快速开始

### 方式一：一键启动（推荐）

```bash
# 启动所有服务（Neo4j + API）
./scripts/start.sh

# 停止所有服务
./scripts/stop.sh
```

### 方式二：手动启动

```bash
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动 Neo4j (使用 Docker)
docker compose up -d neo4j
# 等待 30 秒让 Neo4j 启动

# 5. 导入数据（会自动计算 inferred_genre）
python -m scripts.import_data --path ../MC1_release/MC1_graph.json

# 6. 启动 API 服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 环境要求

- Python 3.9+
- Docker + Docker Compose
- Neo4j Browser 可访问 http://localhost:7474

## 数据说明

### 知识图谱结构

数据来自 VAST 2025 MC1 数据集，包含 17,412 个节点和 37,857 条边：

| 节点类型 | 说明 | 数量 |
|---------|------|------|
| Person | 音乐行业从业者（歌手、制作人、作曲家等） | 11,361 |
| Song | 歌曲 | 3,615 |
| Album | 专辑 | 996 |
| RecordLabel | 唱片公司 | 1,217 |
| MusicalGroup | 乐团/乐队 | 223 |

| 关系类型 | 说明 | 数量 |
|---------|------|------|
| PerformerOf | 表演 | 13,587 |
| RecordedBy | 录制 | 3,798 |
| ComposerOf | 作曲 | 3,290 |
| ProducerOf | 制作 | 3,209 |
| DistributedBy | 发行 | 3,013 |
| LyricistOf | 作词 | 2,985 |
| **InStyleOf** | 风格参考 | 2,289 |
| InterpolatesFrom | 旋律改编 | 1,574 |
| LyricalReferenceTo | 歌词引用 | 1,496 |
| CoverOf | 翻唱 | 1,429 |
| DirectlySamples | 直接采样 | 619 |
| MemberOf | 乐团成员 | 568 |

### InStyleOf 关系说明

根据数据描述文档，`InStyleOf` 关系定义如下：
- **Source**: 只能是 Song 或 Album（以某种风格创作的作品）
- **Target**: 可以是 Song、Album、Person 或 MusicalGroup（风格影响的来源）

为了支持 Person/MusicalGroup 作为风格来源，导入脚本会自动计算 `inferred_genre` 属性：
- Person: 根据其参与的所有歌曲的流派，通过投票计算推断流派
- MusicalGroup: 根据其成员参与的歌曲的流派，通过投票计算推断流派

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 端点

| 模块 | 端点 | 说明 |
|------|------|------|
| 流派演变 | `GET /api/v1/analysis/genre-flow` | 获取流派演变数据（桑基图/河流图） |
| 流派统计 | `GET /api/v1/analysis/genre-stats` | 获取流派统计信息 |
| 艺人画像 | `GET /api/v1/analysis/person-profile` | 获取艺人画像数据（雷达图） |
| 搜索 | `GET /api/v1/search` | 搜索 Person/Song |
| 健康检查 | `GET /health` | 服务健康状态 |

## 项目结构

```
backend/
├── app/
│   ├── api/                    # API 路由
│   │   ├── genre_flow.py       # 流派演变 API
│   │   ├── star_profiler.py   # 艺人画像 API
│   │   └── search.py          # 搜索 API
│   ├── core/                   # 核心模块
│   │   ├── config.py          # 配置管理
│   │   └── database.py       # Neo4j 连接
│   ├── schemas/               # Pydantic 数据模型
│   ├── services/             # 业务逻辑
│   └── main.py               # FastAPI 入口
├── scripts/
│   ├── import_data.py        # 数据导入
│   └── test_services.py      # 测试脚本
└── requirements.txt
```

## 配置

环境变量配置文件 `.env`（可选）：

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
API_PORT=8000
```

---

## API 详细文档

### 1. 流派演变桑基图

**端点**: `GET /api/v1/analysis/genre-flow`

展示流派之间的风格影响流动关系。

#### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `start_year` | int | ✅ | - | 起始年份 (1970-2050) |
| `end_year` | int | ✅ | - | 结束年份 (1970-2050) |
| `metric` | string | ❌ | `style_edges` | 可视化模式：`style_edges`（桑基图）或 `genre_mix`（河流图） |
| `source_genre` | string | ❌ | null | 源流派，用于聚焦特定流派的传播路径 |
| `limit` | int | ❌ | 100 | 返回边数上限 (1-500) |

#### 请求示例

```bash
# 获取 2017-2025 年的流派演变数据
curl "http://localhost:8000/api/v1/analysis/genre-flow?start_year=2017&end_year=2025"

# 只看 Synthwave 的影响传播
curl "http://localhost:8000/api/v1/analysis/genre-flow?start_year=2017&end_year=2025&source_genre=Synthwave"

# 限制返回 50 条边
curl "http://localhost:8000/api/v1/analysis/genre-flow?start_year=2017&end_year=2025&limit=50"
```

#### 响应示例

```json
{
  "data": {
    "nodes": [
      {"id": "Indie Folk", "name": "Indie Folk"},
      {"id": "Doom Metal", "name": "Doom Metal"},
      {"id": "Synthwave", "name": "Synthwave"}
    ],
    "links": [
      {"source": "Indie Folk", "target": "Doom Metal", "value": 15},
      {"source": "Synthwave", "target": "Doom Metal", "value": 13},
      {"source": "Oceanus Folk", "target": "Indie Folk", "value": 12}
    ]
  },
  "meta": {
    "truncated": false,
    "node_count": 23,
    "link_count": 100
  }
}
```

#### 数据说明

- **nodes**: 参与风格流动的流派节点列表
- **links**: 流派之间的风格流动关系
  - `source`: 源流派（风格影响者）
  - `target`: 目标流派（受影响者）
  - `value`: 流动强度（IN_STYLE_OF 关系数量）
- **meta.truncated**: 是否被 limit 截断

#### 前端使用提示

```javascript
// D3.js 桑基图数据格式适配
const sankeyData = {
  nodes: response.data.nodes.map(d => ({...d})),
  links: response.data.links.map(d => ({
    source: d.source,
    target: d.target,
    value: d.value
  }))
};
```

---

### 2. 流派河流图

**端点**: `GET /api/v1/analysis/genre-flow?metric=genre_mix`

展示各流派随时间的歌曲数量变化。

#### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `start_year` | int | ✅ | - | 起始年份 |
| `end_year` | int | ✅ | - | 结束年份 |
| `metric` | string | ❌ | - | 必须设为 `genre_mix` |
| `limit` | int | ❌ | 100 | 返回流派数量上限 |

#### 响应示例

```json
{
  "data": {
    "series": [
      {
        "genre": "Indie Folk",
        "points": [
          {"year": 2017, "value": 45},
          {"year": 2018, "value": 52},
          {"year": 2019, "value": 61}
        ]
      },
      {
        "genre": "Doom Metal",
        "points": [
          {"year": 2017, "value": 23},
          {"year": 2018, "value": 28}
        ]
      }
    ]
  },
  "meta": {
    "node_count": 15
  }
}
```

#### 前端使用提示

```javascript
// 河流图数据格式
const streamData = response.data.series.map(s => ({
  name: s.genre,
  series: s.points.map(p => ({ date: p.year, value: p.value }))
}));
```

---

### 3. 艺人画像

**端点**: `GET /api/v1/analysis/person-profile`

获取艺人的多维度画像数据，用于雷达图可视化。

#### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `person_ids` | string | ✅ | - | 艺人 ID，多个用逗号分隔，最多 20 个 |
| `start_year` | int | ❌ | null | 起始年份筛选 |
| `end_year` | int | ❌ | null | 结束年份筛选 |
| `normalized` | bool | ❌ | false | 是否返回归一化数据 (0-1) |

#### 请求示例

```bash
# 获取单个艺人
curl "http://localhost:8000/api/v1/analysis/person-profile?person_ids=123"

# 获取多个艺人
curl "http://localhost:8000/api/v1/analysis/person-profile?person_ids=123,456,789"

# 获取归一化数据（适合雷达图）
curl "http://localhost:8000/api/v1/analysis/person-profile?person_ids=123,456&normalized=true"

# 按时间筛选
curl "http://localhost:8000/api/v1/analysis/person-profile?person_ids=123,456&start_year=2017&end_year=2025"
```

#### 响应示例（原始数据）

```json
{
  "data": {
    "profiles": [
      {
        "person_id": "123",
        "name": "John Doe",
        "metrics": {
          "song_count": 45,
          "notable_count": 12,
          "notable_rate": 0.267,
          "active_years": 15,
          "unique_collaborators": 23,
          "genre_entropy": 2.341,
          "degree": 156,
          "pagerank": 0.156,
          "song_cowrite_count": 18,
          "style_influence_count": 5
        },
        "top_genres": ["Indie Folk", "Americana", "Dream Pop"]
      }
    ],
    "dimensions": ["song_count", "notable_rate", "active_years", "unique_collaborators", "genre_entropy", "degree", "pagerank"]
  },
  "meta": {
    "truncated": false,
    "total_hint": 1
  }
}
```

#### 响应示例（归一化数据）

```json
{
  "data": {
    "profiles": [
      {
        "person_id": "123",
        "name": "John Doe",
        "metrics": {
          "song_count": 0.75,
          "notable_rate": 0.5,
          "active_years": 0.85,
          "unique_collaborators": 0.62,
          "genre_entropy": 0.78,
          "degree": 0.45,
          "pagerank": 0.45
        },
        "raw_metrics": {
          "song_count": 45,
          "notable_rate": 0.267,
          ...
        }
      }
    ],
    "dimensions": ["song_count", "notable_rate", ...],
    "normalization": {
      "type": "min-max",
      "ranges": {
        "song_count": {"min": 10, "max": 60}
      }
    }
  }
}
```

#### 指标说明

| 指标 | 说明 | 数据范围 |
|------|------|---------|
| `song_count` | 歌曲数量 | 0 ~ ∞ |
| `notable_count` | 代表作数量 | 0 ~ song_count |
| `notable_rate` | 代表作比例 | 0.0 ~ 1.0 |
| `active_years` | 活跃年数跨度 | 0 ~ (end_year - start_year) |
| `unique_collaborators` | 独立合作者数量 | 0 ~ ∞ |
| `genre_entropy` | 流派多样性（信息熵） | 0.0 ~ log2(流派数) |
| `degree` | 图度数（连接数） | 0 ~ ∞ |
| `pagerank` | PageRank 中心性 | 0.0 ~ 1.0 |
| `song_cowrite_count` | 合唱/合著歌曲数 | 0 ~ song_count |
| `style_influence_count` | 风格影响力（被引用次数） | 0 ~ ∞ |

#### 前端使用提示

```javascript
// 雷达图数据适配
const radarData = response.data.profiles.map(person => ({
  personId: person.person_id,
  name: person.name,
  axes: response.data.dimensions.map(dim => ({
    axis: dim,
    value: person.metrics[dim]  // 归一化后直接用于雷达图
  }))
}));

// 获取艺人 ID 用于绑定交互
const personIds = response.data.profiles.map(p => p.person_id);
```

---

### 4. 艺人画像（单个）

**端点**: `GET /api/v1/analysis/person-profile/{person_id}`

获取单个艺人的详细信息，便捷端点。

#### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `person_id` | string | ✅ | - | 艺人 ID（路径参数） |
| `start_year` | int | ❌ | null | 起始年份 |
| `end_year` | int | ❌ | null | 结束年份 |

#### 请求示例

```bash
curl "http://localhost:8000/api/v1/analysis/person-profile/123"
curl "http://localhost:8000/api/v1/analysis/person-profile/123?start_year=2017&end_year=2025"
```

---

### 5. 搜索

**端点**: `GET /api/v1/search`

全局搜索艺人或歌曲。

#### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `q` | string | ✅ | - | 搜索关键词（1-100字符） |
| `type` | string | ❌ | `all` | 搜索类型：`person`、`song`、`all` |
| `limit` | int | ❌ | 20 | 返回结果上限 (1-100) |

#### 请求示例

```bash
# 搜索所有类型
curl "http://localhost:8000/api/v1/search?q=indie"

# 只搜索艺人
curl "http://localhost:8000/api/v1/search?q=john&type=person"

# 只搜索歌曲
curl "http://localhost:8000/api/v1/search?q=folk&type=song"
```

#### 响应示例

```json
{
  "results": [
    {
      "id": "123",
      "label": "John Doe",
      "type": "person",
      "subtitle": "艺人 | John Doe"
    },
    {
      "id": "456",
      "label": "Midnight Folk",
      "type": "song",
      "subtitle": "Indie Folk | 2020 | ★"
    }
  ],
  "total": 2,
  "query": "indie"
}
```

#### 返回字段说明

| 字段 | 说明 |
|------|------|
| `id` | 艺人或歌曲的 original_id，可用于 `person-profile` 查询 |
| `label` | 显示名称（艺人用 stage_name 或 name，歌曲用 title） |
| `type` | 类型：`person` 或 `song` |
| `subtitle` | 附加信息（艺人显示本名，歌曲显示流派/年份/★标记） |

#### 前端使用提示

```javascript
// 搜索结果选择后跳转
function onSelectSearchResult(result) {
  if (result.type === 'person') {
    // 跳转到艺人详情页
    router.push(`/artist/${result.id}`);
  } else {
    // 跳转到歌曲详情页
    router.push(`/song/${result.id}`);
  }
}

// 获取艺人 ID 用于画像查询
const selectedPersonId = searchResult.id;
```

---

### 6. 流派统计

**端点**: `GET /api/v1/analysis/genre-stats`

获取所有流派的歌曲数量统计，用于下拉选择器和过滤器。

#### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `start_year` | int | ✅ | - | 起始年份 |
| `end_year` | int | ✅ | - | 结束年份 |

#### 请求示例

```bash
curl "http://localhost:8000/api/v1/analysis/genre-stats?start_year=2017&end_year=2025"
```

#### 响应示例

```json
{
  "data": [
    {"genre": "Indie Folk", "song_count": 156},
    {"genre": "Doom Metal", "song_count": 89},
    {"genre": "Dream Pop", "song_count": 72}
  ],
  "meta": {}
}
```

---

## 统一响应格式

所有分析 API 返回统一格式：

```json
{
  "data": { ... },      // 业务数据
  "meta": {              // 元信息
    "truncated": false,  // 是否被截断
    "node_count": 23,    // 节点数量（桑基图/河流图）
    "link_count": 100,   // 边数量（桑基图）
    "total_hint": 5      // 总数提示（艺人画像）
  }
}
```

## 错误响应

```json
{
  "detail": "错误描述"
}
```

常见错误码：
- `400`: 参数错误（年份范围错误、格式错误）
- `404`: 找不到指定艺人
- `500`: 服务器内部错误
