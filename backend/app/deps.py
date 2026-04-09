from collections.abc import AsyncGenerator

from fastapi import Request
from neo4j import AsyncSession


async def get_neo4j_session(request: Request) -> AsyncGenerator[AsyncSession | None, None]:
    driver = getattr(request.app.state, "neo4j_driver", None)
    if driver is None:
        yield None
        return
    async with driver.session() as session:
        yield session
