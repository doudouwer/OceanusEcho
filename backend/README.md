# OceanusEcho 后端

后端 API 服务，基于 FastAPI + Neo4j 构建，用于音乐知识图谱分析。

## 技术栈

| 组件 | 技术 |
|------|------|
| API 框架 | FastAPI 0.109.0 |
| 数据库 | Neo4j 5.16.0（兼容 5.x） |
| Python | 3.9+ |

## 启动方式

### 方式一：一键启动（推荐）

请在仓库根目录执行，因为 `docker-compose.yml` 放在项目根目录。

```bash
./scripts/start.sh
./scripts/stop.sh
```

`start.sh` 会依次完成：

1. 检查 Docker 是否安装并运行
2. 启动 Neo4j
3. 询问是否导入 `MC1_graph.json`
4. 创建并激活后端虚拟环境
5. 安装 Python 依赖
6. 启动 FastAPI

### 方式二：手动启动

```bash
# 1. 进入项目根目录
cd /mnt/d/code/assignment/OceanusEcho

# 2. 启动 Neo4j
docker compose up -d neo4j
sleep 30

# 3. 进入后端目录
cd backend

# 4. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 5. 安装依赖
pip install -r requirements.txt

# 6. 导入数据
python -m scripts.import_data --path ../MC1_release/MC1_graph.json

# 7. 启动 API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 环境要求

- Python 3.9+
- Docker + Docker Compose
- Neo4j Browser 可访问 http://localhost:7474
- 启动 API 之前必须先让 Neo4j 可用，否则后端会在启动阶段直接失败

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
| InStyleOf | 风格参考 | 2,289 |
| InterpolatesFrom | 旋律改编 | 1,574 |
| LyricalReferenceTo | 歌词引用 | 1,496 |
| CoverOf | 翻唱 | 1,429 |
| DirectlySamples | 直接采样 | 619 |
| MemberOf | 乐团成员 | 568 |

### InStyleOf 关系说明

根据数据描述文档，`InStyleOf` 关系定义如下：

- **Source**: 只能是 Song 或 Album
- **Target**: 可以是 Song、Album、Person 或 MusicalGroup

为了支持 Person/MusicalGroup 作为风格来源，导入脚本会自动计算 `inferred_genre`：

- Person: 根据其参与歌曲的流派，通过投票推断
- MusicalGroup: 根据其成员参与歌曲的流派，通过投票推断

### 本地图数据工具

项目中保留了 `MC1_release/MC1_graph.json` 的本地读取工具，用于开发、分析和脚本级验证。

当前主 API 启动流程仍然要求 Neo4j 可用；如果 Neo4j 连接失败，FastAPI 会直接报错，避免把问题藏起来。

## API 文档

启动服务后访问：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 端点

| 模块 | 端点 | 说明 |
|------|------|------|
| 职业时轴 | `GET /api/v1/analysis/career-track` | 获取 Sailor Shift 等艺人的职业时轴数据 |
| 影响力网络 | `POST /api/v1/graph/subgraph` | 获取局部影响力子图 |
| 邻居展开 | `GET /api/v1/graph/expand/{node_id}` | 展开某个节点的邻居 |
| 流派演变 | `GET /api/v1/analysis/genre-flow` | 获取流派演变数据（桑基图/河流图） |
| 流派统计 | `GET /api/v1/analysis/genre-stats` | 获取流派统计信息 |
| 艺人画像 | `GET /api/v1/analysis/person-profile` | 获取艺人画像数据（雷达图） |
| 搜索 | `GET /api/v1/search` | 搜索 Person/Song |
| 健康检查 | `GET /health` | 服务健康状态 |

## 项目结构

```text
backend/
├── app/
│   ├── api/
│   │   ├── career_arc.py       # 职业时轴 API
│   │   ├── genre_flow.py       # 流派演变 API
│   │   ├── graph.py            # 影响力网络 API
│   │   ├── search.py           # 搜索 API
│   │   └── star_profiler.py    # 艺人画像 API
│   ├── core/
│   │   ├── config.py           # 配置管理
│   │   └── database.py        # Neo4j 连接
│   ├── schemas/
│   │   ├── analysis.py         # Career Arc / Influence Galaxy 数据结构
│   │   ├── graph.py            # 图结构请求与返回
│   │   └── models.py           # 通用 API 模型
│   ├── services/
│   │   ├── career_arc_service.py
│   │   ├── genre_flow_service.py
│   │   ├── influence_galaxy_service.py
│   │   ├── local_graph.py
│   │   ├── neo4j_serialize.py
│   │   └── star_profiler_service.py
│   ├── constants.py
│   └── main.py
├── scripts/
│   ├── import_data.py
│   └── test_services.py
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

## 测试与验收

### 1. 服务冒烟测试

在后端目录运行：

```bash
cd /mnt/d/code/assignment/OceanusEcho/backend
python -m scripts.test_services
```

该脚本会检查：

- 模块导入
- 配置加载
- Pydantic 模型
- API 路由挂载
- Neo4j 查询连通性

### 2. 四个图模块的手动验收

建议在 `uvicorn` 已启动、Neo4j 已导入数据后，逐个检查以下接口：

| 图模块 | 验收接口 | 重点检查 |
|------|------|------|
| Career Arc | `GET /api/v1/analysis/career-track?person_name=Sailor%20Shift` | 是否返回 `summary`、`by_year`、`works` |
| Influence Galaxy | `POST /api/v1/graph/subgraph` | 是否返回 `graph.nodes`、`graph.links`、`clusters`、`bridge_nodes` |
| Genre Flow | `GET /api/v1/analysis/genre-flow?metric=style_edges` / `metric=genre_mix` | 是否分别返回 `nodes+links` 和 `series` |
| Star Profiler | `GET /api/v1/analysis/person-profile?person_ids=...` | 是否返回 `profiles`、`dimensions`、归一化指标 |

### 3. 推荐的 curl 验证命令

#### Career Arc

```bash
curl "http://localhost:8000/api/v1/analysis/career-track?person_name=Sailor%20Shift&start_year=2023&end_year=2040"
curl "http://localhost:8000/api/v1/analysis/career-track?person_id=17255&start_year=2023&end_year=2040"
```

#### Influence Galaxy

```bash
curl -X POST "http://localhost:8000/api/v1/graph/subgraph" \
  -H "Content-Type: application/json" \
  -d '{
    "start_year": 2023,
    "end_year": 2040,
    "genres": ["Oceanus Folk"],
    "seed_person_ids": ["17255"],
    "rel_types": ["PERFORMER_OF","IN_STYLE_OF","MEMBER_OF"],
    "limit_nodes": 80,
    "only_notable_songs": false
  }'

curl "http://localhost:8000/api/v1/graph/expand/17255?rel_types=PERFORMER_OF,IN_STYLE_OF&direction=both&limit=50"
```

#### Genre Flow

```bash
curl "http://localhost:8000/api/v1/analysis/genre-flow?start_year=2017&end_year=2025&metric=style_edges&limit=50"
curl "http://localhost:8000/api/v1/analysis/genre-flow?start_year=2017&end_year=2025&metric=genre_mix"
curl "http://localhost:8000/api/v1/analysis/genre-stats?start_year=2017&end_year=2025"
```

#### Star Profiler

```bash
curl "http://localhost:8000/api/v1/analysis/person-profile?person_ids=17255,123,456&normalized=true"
curl "http://localhost:8000/api/v1/analysis/person-profile/17255"
```

#### Search / Health

```bash
curl "http://localhost:8000/api/v1/search?q=Sailor&type=all&limit=5"
curl "http://localhost:8000/health"
```

---

## 统一响应格式

所有分析 API 返回统一格式：

```json
{
  "data": { ... },
  "meta": {
    "truncated": false,
    "node_count": 23,
    "link_count": 100,
    "total_hint": 5
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

- `400`: 参数错误
- `404`: 找不到指定艺人
- `500`: 服务器内部错误
