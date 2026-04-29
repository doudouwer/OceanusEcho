# OceanusEcho Backend

FastAPI + Neo4j 后端服务，提供 Career Arc / Influence Galaxy / Genre Flow / Star Profiler / Search 接口。

## 运行前提

- Python 3.9+
- Docker + Docker Compose
- Neo4j 可访问（默认 `bolt://127.0.0.1:7687`）

## 快速启动

```bash
# 项目根目录
./scripts/start.sh
```

## 手动启动

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 启动 Neo4j（在项目根目录）
cd ..
docker compose up -d neo4j
# 等待 Bolt 真正可连通（比 compose health 状态更可靠）
until docker exec oceanecho-neo4j cypher-shell -u neo4j -p password "RETURN 1;" >/dev/null 2>&1; do
  echo "waiting neo4j bolt ready..."
  sleep 1
done
cd backend

# 导入数据（首次或需要重建时）
python -m scripts.import_data --path ../MC1_release/MC1_graph.json

# 启动 API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 环境变量

复制 `backend/.env.example` 为 `backend/.env`，常用字段：

```bash
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here
API_PORT=8000
API_DEBUG=true
API_PREFIX=/api/v1
```

说明：
- 后端为在线严格模式。启动阶段会等待 Neo4j 就绪；若重试失败，`uvicorn` 会直接启动失败（fail fast），不做静默兜底。
- 运行中若连接异常，`/health` 返回 HTTP `503`。
- 若本机设置了 `HTTP_PROXY/HTTPS_PROXY`，旧版 healthcheck 可能误判 `unhealthy`；当前 compose 已改为 `wget --no-proxy`。

## 接口清单（当前代码实现）

- `GET /health`
- `GET /api/v1/search`
- `GET /api/v1/analysis/career-track`
- `GET /api/v1/analysis/genre-flow`
- `GET /api/v1/analysis/genre-stats`
- `GET /api/v1/analysis/person-profile`
- `POST /api/v1/graph/subgraph`
- `GET /api/v1/graph/expand/{node_id}`

## Influence Galaxy（当前实现要点）

- `subgraph` 支持：`rel_types`、`max_hops`、`start_year/end_year`、`genres`、`only_notable_songs`、`limit_nodes`
- 返回结构包含：
  - `graph.nodes / graph.links`
  - `seed_people`
  - `clusters`（社区摘要）
  - `bridge_nodes`（桥接节点评分 Top）
- `expand` 支持与 `subgraph` 一致的关系与过滤参数，用于前端增量展开。

## 在线验证与效果预览

确保 API 已启动后运行：

```bash
cd backend
python -m scripts.test_services
```

脚本会：
- 验证健康状态与核心接口可用性
- 拉取并汇总 Galaxy `subgraph + expand` 的关键统计
- 输出结果到 `/tmp/oceanusecho-preview/run_*/`

可选参数示例：

```bash
python -m scripts.test_services \
  --base-url http://127.0.0.1:8000 \
  --seed-person-id 17255 \
  --start-year 2023 \
  --end-year 2040 \
  --genres "Oceanus Folk"
```

## 参考文档

- 后端接口与数据层说明：`docs/backend-architecture.md`
- 前端联动说明：`docs/frontend-architecture.md`
