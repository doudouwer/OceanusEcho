from fastapi import APIRouter

from app.routers import analysis, graph, search

api_router = APIRouter()
api_router.include_router(graph.router)
api_router.include_router(analysis.router)
api_router.include_router(search.router)
