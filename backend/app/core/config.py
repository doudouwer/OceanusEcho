from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置类"""

    # Neo4j 配置
    neo4j_uri: str = Field(default="bolt://127.0.0.1:7687", validation_alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", validation_alias="NEO4J_USER")
    neo4j_password: str = Field(default="password", validation_alias="NEO4J_PASSWORD")

    # API 配置
    api_host: str = Field(default="0.0.0.0", validation_alias="API_HOST")
    api_port: int = Field(default=8000, validation_alias="API_PORT")
    api_debug: bool = Field(default=True, validation_alias="API_DEBUG")

    # 数据配置
    data_path: str = Field(default="../MC1_release/MC1_graph.json", validation_alias="DATA_PATH")

    # API 路径前缀
    api_prefix: str = Field(default="/api/v1", validation_alias="API_PREFIX")

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """获取缓存的配置实例"""
    return Settings()
