#!/bin/bash

# OceanusEcho 一键启动（Neo4j + FastAPI）
# 用法:
#   ./scripts/start.sh              # 启动 Neo4j 与 API，不导入数据
#   ./scripts/start.sh --import     # 若存在 MC1_graph.json，则先导入 Neo4j

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_DIR/backend"
DATA_JSON="$PROJECT_DIR/MC1_release/MC1_graph.json"
API_PORT="${API_PORT:-8000}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-password}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

DO_IMPORT=0
for arg in "$@"; do
  case "$arg" in
    --import) DO_IMPORT=1 ;;
    -h|--help)
      echo "用法: $0 [--import]"
      exit 0
      ;;
    *)
      echo -e "${RED}未知参数: $arg${NC}"
      echo "用法: $0 [--import]"
      exit 1
      ;;
  esac
done

echo "=========================================="
echo "  OceanusEcho 后端服务启动"
echo "=========================================="

check_docker() {
  if ! command -v docker &>/dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    exit 1
  fi

  if ! docker info &>/dev/null; then
    echo -e "${RED}错误: Docker 未运行（请先打开 Docker Desktop）${NC}"
    exit 1
  fi
}

wait_for_neo4j() {
  local max="${1:-120}"
  local i=0

  echo -e "${YELLOW}等待 Neo4j Bolt 就绪...${NC}"
  until docker exec oceanecho-neo4j cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" "RETURN 1 AS ok;" &>/dev/null; do
    i=$((i + 1))
    if [[ "$i" -ge "$max" ]]; then
      echo -e "${RED}错误: Neo4j 多次重试后仍不可连接。请查看: docker logs oceanecho-neo4j${NC}"
      exit 1
    fi
    sleep 2
  done

  echo -e "${GREEN}✓ Neo4j 已就绪${NC}"
}

ensure_port_free() {
  local port="$1"
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN &>/dev/null; then
    echo -e "${RED}错误: 端口 $port 已被占用，无法启动 FastAPI。${NC}"
    lsof -nP -iTCP:"$port" -sTCP:LISTEN || true
    echo ""
    echo "如果确认是旧的 uvicorn，可以执行: kill <PID>"
    exit 1
  fi
}

start_neo4j() {
  echo -e "\n${YELLOW}[1/4] 启动 Neo4j...${NC}"
  cd "$PROJECT_DIR"
  docker compose up -d neo4j
  wait_for_neo4j 120
  echo "  - Neo4j Browser: http://localhost:7474"
  echo "  - Bolt: bolt://localhost:7687"
}

setup_python() {
  echo -e "\n${YELLOW}[2/4] Python 虚拟环境与依赖...${NC}"
  cd "$BACKEND_DIR"

  if [[ ! -d venv ]]; then
    python3 -m venv venv
  fi

  # shellcheck source=/dev/null
  source venv/bin/activate
  pip install -q -r requirements.txt
  echo -e "${GREEN}✓ 依赖就绪${NC}"
}

import_data_maybe() {
  echo -e "\n${YELLOW}[3/4] 数据导入...${NC}"
  cd "$BACKEND_DIR"

  # shellcheck source=/dev/null
  source venv/bin/activate

  if [[ "$DO_IMPORT" -ne 1 ]]; then
    echo -e "${YELLOW}跳过导入（需要时运行: ./scripts/start.sh --import）${NC}"
    return 0
  fi

  if [[ ! -f "$DATA_JSON" ]]; then
    echo -e "${RED}错误: 未找到数据文件 $DATA_JSON${NC}"
    exit 1
  fi

  python -m scripts.import_data --path "$DATA_JSON"
  echo -e "${GREEN}✓ 数据导入完成${NC}"
}

start_api() {
  echo -e "\n${YELLOW}[4/4] 启动 FastAPI...${NC}"
  ensure_port_free "$API_PORT"

  cd "$BACKEND_DIR"
  # shellcheck source=/dev/null
  source venv/bin/activate

  echo -e "${GREEN}==========================================${NC}"
  echo -e "${GREEN}  正在启动 API: http://localhost:${API_PORT}/docs${NC}"
  echo -e "${GREEN}==========================================${NC}"
  exec uvicorn app.main:app --reload --host 0.0.0.0 --port "$API_PORT"
}

main() {
  check_docker
  start_neo4j
  setup_python
  import_data_maybe
  start_api
}

main "$@"
