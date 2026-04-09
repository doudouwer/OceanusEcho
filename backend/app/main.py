"""
OceanusEcho Backend - FastAPI 应用入口

面向「多视图联动（Linked Multiple Views）」的音乐产业图谱可视化后端服务
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core.config import get_settings
from .core.database import neo4j_connection
from .api import genre_flow, star_profiler, search

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("正在连接 Neo4j 数据库...")
    try:
        neo4j_connection.connect()
        if neo4j_connection.verify_connectivity():
            print("✓ Neo4j 连接成功")
        else:
            print("⚠ Neo4j 连接验证失败，请检查配置")
    except Exception as e:
        print(f"⚠ Neo4j 连接失败: {e}")
    
    yield
    
    # 关闭时
    print("关闭 Neo4j 连接...")
    neo4j_connection.close()


# 创建 FastAPI 应用
app = FastAPI(
    title="OceanusEcho API",
    description="""
## OceanusEcho 后端 API

面向「多视图联动（Linked Multiple Views）」的音乐产业图谱可视化系统的后端服务。

### 核心功能

- **流派演变 (Genre Flow)**: 桑基图和河流图数据
- **艺人画像 (Star Profiler)**: 多维度艺人特征数据
- **全局搜索**: Person 和 Song 搜索

### 技术栈

- **框架**: FastAPI
- **数据库**: Neo4j
- **数据格式**: JSON

### 更多信息

请参阅 [后端架构文档](../../docs/backend-architecture.md)
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册路由
app.include_router(
    genre_flow.router,
    prefix=settings.api_prefix,
    tags=["流派演变 (Genre Flow)"]
)

app.include_router(
    star_profiler.router,
    prefix=settings.api_prefix,
    tags=["艺人画像 (Star Profiler)"]
)

app.include_router(
    search.router,
    prefix=settings.api_prefix,
    tags=["搜索"]
)


@app.get("/", tags=["健康检查"])
async def root():
    """根路径 - 服务信息"""
    return {
        "name": "OceanusEcho API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查端点"""
    neo4j_status = "connected" if neo4j_connection.verify_connectivity() else "disconnected"
    
    return {
        "status": "healthy",
        "neo4j": neo4j_status,
        "api_prefix": settings.api_prefix
    }
