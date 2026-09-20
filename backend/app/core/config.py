from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

import yaml
from pydantic import BaseModel, Field


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "deployment").is_dir():
            return parent
    raise RuntimeError("找不到仓库根（缺少 deployment/）")


class PostgresSettings(BaseModel):
    host: str
    port: int
    database: str
    user: str
    password: str


class RedisSettings(BaseModel):
    host: str
    port: int
    password: str | None = None


class Settings(BaseModel):
    listen_host: str = "0.0.0.0"
    listen_port: int = 8000
    cors_origins: list[str] = Field(default_factory=list)
    postgres: PostgresSettings
    redis: RedisSettings
    api_base: str | None = None
    token_ttl_seconds: int = 86400
    uvicorn_workers: int = 2
    db_pool_size: int = 10
    db_pool_max_overflow: int = 10
    db_pool_timeout: int = 30

    @property
    def async_database_url(self) -> str:
        user = quote_plus(self.postgres.user)
        password = quote_plus(self.postgres.password)
        return (
            f"postgresql+asyncpg://{user}:{password}"
            f"@{self.postgres.host}:{self.postgres.port}/{self.postgres.database}"
        )


def load_yaml(path: Path) -> Settings:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RuntimeError(f"配置不是映射：{path}")
    return Settings.model_validate(raw)


@lru_cache
def get_settings() -> Settings:
    env = os.environ.get("ADPILOT_ENV", "dev").strip().lower() or "dev"
    if env not in {"dev", "prod"}:
        raise RuntimeError("ADPILOT_ENV 只允许 dev 或 prod")
    path = repo_root() / "deployment" / f"{env}.yaml"
    if not path.is_file():
        raise RuntimeError(f"缺少配置文件：{path}")
    return load_yaml(path)
