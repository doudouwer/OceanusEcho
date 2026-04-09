#!/bin/bash

# OceanusEcho 停止脚本
# 用法: ./scripts/stop.sh

set -e

echo "=========================================="
echo "  OceanusEcho 服务停止"
echo "=========================================="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# 停止并移除容器
echo "停止 Neo4j 容器..."
docker compose down 2>/dev/null || true

echo ""
echo -e "\033[0;32m✓ 所有服务已停止\033[0m"
