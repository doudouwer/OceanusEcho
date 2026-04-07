from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from neo4j import AsyncGraphDatabase

from app.config import settings
from app.routers import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    driver = None
    if settings.neo4j_configured:
        drv = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        try:
            await drv.verify_connectivity()
            driver = drv
        except Exception:
            await drv.close()
            driver = None
    app.state.neo4j_driver = driver
    yield
    if driver is not None:
        await driver.close()


app = FastAPI(
    title="OceanusEcho API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "neo4j": "connected" if getattr(app.state, "neo4j_driver", None) else "offline"}
