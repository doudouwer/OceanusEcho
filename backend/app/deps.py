from collections.abc import AsyncGenerator
from typing import Optional

from fastapi import Request
from neo4j import AsyncSession

from app.core.database import get_neo4j_async_driver


async def get_neo4j_session(request: Request) -> AsyncGenerator[Optional[AsyncSession], None]:
    driver = getattr(request.app.state, "neo4j_driver", None)
    if driver is None:
        yield None
        return
    async with driver.session() as session:
        yield session


async def get_neo4j_driver():
    """获取异步驱动，支持启动时预热和运行时按需两种模式。"""
    return get_neo4j_async_driver()
