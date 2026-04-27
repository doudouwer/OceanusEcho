from neo4j import GraphDatabase
from neo4j import AsyncGraphDatabase
from typing import Optional
from contextlib import contextmanager
from .config import get_settings

settings = get_settings()


class Neo4jConnection:
    """Neo4j 数据库连接管理器（同步 + 异步）"""

    _instance: Optional['Neo4jConnection'] = None
    _driver = None
    _async_driver = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def connect(self) -> None:
        """建立同步数据库连接"""
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )

    def connect_async(self) -> None:
        """建立异步数据库连接"""
        if self._async_driver is None:
            self._async_driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )

    def close(self) -> None:
        """关闭同步数据库连接"""
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    async def close_async(self) -> None:
        """关闭同步 + 异步数据库连接"""
        self.close()
        if self._async_driver is not None:
            await self._async_driver.close()
            self._async_driver = None

    def get_driver(self):
        """获取同步驱动实例"""
        if self._driver is None:
            self.connect()
        return self._driver

    def get_async_driver(self):
        """获取异步驱动实例"""
        if self._async_driver is None:
            self.connect_async()
        return self._async_driver

    @contextmanager
    def session(self, **kwargs):
        """上下文管理器：自动管理同步会话"""
        driver = self.get_driver()
        session = driver.session(**kwargs)
        try:
            yield session
        finally:
            session.close()

    def verify_connectivity(self) -> bool:
        """验证连接是否正常"""
        try:
            with self.session() as session:
                result = session.run("RETURN 1")
                result.consume()
            return True
        except Exception as e:
            print(f"Neo4j 连接验证失败: {e}")
            return False


# 全局单例实例
neo4j_connection = Neo4jConnection()


def get_neo4j_connection() -> Neo4jConnection:
    """获取 Neo4j 连接实例（同步）"""
    return neo4j_connection


def get_neo4j_async_driver():
    """获取异步驱动实例"""
    return neo4j_connection.get_async_driver()
