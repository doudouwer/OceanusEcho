"""
OceanusEcho Backend - FastAPI 应用入口

面向「多视图联动（Linked Multiple Views）」的音乐产业图谱可视化后端服务
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core.config import get_settings
from .core.database import neo4j_connection
from .routers import analysis, graph, search

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("正在连接 Neo4j 数据库...")
    try:
        neo4j_connection.connect()
        if neo4j_connection.verify_connectivity():
            print("✓ Neo4j 同步连接成功")
    except Exception as e:
        print(f"⚠ Neo4j 同步连接失败: {e}")

    try:
        neo4j_connection.connect_async()
        async_driver = neo4j_connection.get_async_driver()
        await async_driver.verify_connectivity()
        app.state.neo4j_driver = async_driver
        print("✓ Neo4j 异步驱动初始化成功")
    except Exception as e:
        app.state.neo4j_driver = None
        print(f"⚠ Neo4j 异步驱动初始化失败: {e}")

    yield

    print("关闭 Neo4j 连接...")
    neo4j_connection.close()


app = FastAPI(
    title="OceanusEcho API",
    description="""
## OceanusEcho 后端 API

面向「多视图联动（Linked Multiple Views）」的音乐产业图谱可视化系统的后端服务。

### 核心功能

- **职业时轴 (Career Arc)**: 艺人职业轨迹与作品年表
- **影响力网络 (Influence Galaxy)**: 关系网络与影响力分析
- **流派演变 (Genre Flow)**: 桑基图和河流图数据
- **艺人画像 (Star Profiler)**: 多维度艺人特征数据
- **全局搜索**: Person 和 Song 搜索

### 技术栈

- **框架**: FastAPI (异步)
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


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    analysis.router,
    prefix=settings.api_prefix,
    tags=["分析视图"]
)

app.include_router(
    graph.router,
    prefix=settings.api_prefix,
    tags=["关系网络"]
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
    sync_ok = neo4j_connection.verify_connectivity()
    async_driver = getattr(app.state, "neo4j_driver", None)
    async_ok = async_driver is not None
    return {
        "status": "healthy" if (sync_ok and async_ok) else "degraded",
        "neo4j_sync": "connected" if sync_ok else "disconnected",
        "neo4j_async": "connected" if async_ok else "disconnected",
        "api_prefix": settings.api_prefix
    }
