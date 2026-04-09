#!/bin/bash

# OceanusEcho 启动脚本
# 用法: ./scripts/start.sh

set -e

echo "=========================================="
echo "  OceanusEcho 后端服务启动"
echo "=========================================="

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_DIR/backend"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查 Docker 是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}错误: Docker 未安装${NC}"
        echo "请从 https://docker.com 下载安装 Docker Desktop"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        echo -e "${RED}错误: Docker 未运行${NC}"
        echo "请启动 Docker Desktop"
        exit 1
    fi
}

# 启动 Neo4j
start_neo4j() {
    echo -e "\n${YELLOW}[1/3] 启动 Neo4j 数据库...${NC}"

    cd "$PROJECT_DIR"

    # 检查 docker-compose 是否运行
    if docker compose ps neo4j &> /dev/null; then
        if docker compose ps neo4j | grep -q "Up"; then
            echo -e "${GREEN}✓ Neo4j 已在运行${NC}"
        else
            echo -e "${YELLOW}Neo4j 已停止，正在重启...${NC}"
            docker compose up -d neo4j
        fi
    else
        echo -e "${YELLOW}首次启动，创建 Neo4j 容器...${NC}"
        docker compose up -d neo4j

        echo -e "${YELLOW}等待 Neo4j 启动（可能需要 30 秒）...${NC}"
        sleep 30
    fi

    echo -e "${GREEN}✓ Neo4j 启动完成${NC}"
    echo "  - Neo4j Browser: http://localhost:7474"
    echo "  - Bolt 连接: bolt://localhost:7687"
    echo "  - 默认账号: neo4j / password"
}

# 导入数据（可选）
import_data() {
    echo -e "\n${YELLOW}[2/3] 检查数据导入...${NC}"

    # 检查是否需要导入数据
    cd "$BACKEND_DIR"

    read -p "是否导入数据到 Neo4j? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}开始导入数据...（可能需要几分钟）${NC}"
        source venv/bin/activate
        python -m scripts.import_data --path ../MC1_release/MC1_graph.json
        echo -e "${GREEN}✓ 数据导入完成${NC}"
    else
        echo -e "${YELLOW}跳过数据导入${NC}"
    fi
}

# 启动 FastAPI
start_api() {
    echo -e "\n${YELLOW}[3/3] 启动 FastAPI 服务...${NC}"

    cd "$BACKEND_DIR"

    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}创建 Python 虚拟环境...${NC}"
        python3 -m venv venv
    fi

    source venv/bin/activate

    # 检查依赖
    pip install -q -r requirements.txt 2>/dev/null || true

    echo -e "${GREEN}✓ FastAPI 服务启动完成${NC}"
    echo -e "\n${GREEN}==========================================${NC}"
    echo -e "${GREEN}  所有服务已启动！${NC}"
    echo -e "${GREEN}==========================================${NC}"
    echo ""
    echo "  API 文档: http://localhost:8000/docs"
    echo "  ReDoc:    http://localhost:8000/redoc"
    echo ""

    # 启动服务
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

# 主流程
main() {
    check_docker
    start_neo4j
    import_data
    start_api
}

main "$@"
