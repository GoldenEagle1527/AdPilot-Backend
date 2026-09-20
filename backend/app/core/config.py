from __future__ import annotations

import os
import socket
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

import yaml
from pydantic import BaseModel, Field

# Compose 服务名只在容器网里有效；本机跑测试/alembic 时改连已映射的 127.0.0.1。
_COMPOSE_SERVICE_HOSTS = frozenset({"postgres", "redis"})
_HOST_FALLBACK = "127.0.0.1"


def _host_for_this_process(host: str) -> str:
    if host not in _COMPOSE_SERVICE_HOSTS:
        return host
    try:
        socket.getaddrinfo(host, None)
    except OSError:
        return _HOST_FALLBACK
    return host


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


class ChangduSettings(BaseModel):
    base_url: str = "https://openapi.changdupingtai.com"
    distributor_id: str = ""
    secret_key: str = ""
    sync_interval_seconds: int = 1800


class Settings(BaseModel):
    listen_host: str = "0.0.0.0"
    listen_port: int = 8000
    cors_origins: list[str] = Field(default_factory=list)
    postgres: PostgresSettings
    redis: RedisSettings
    changdu: ChangduSettings = Field(default_factory=ChangduSettings)
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
    settings = Settings.model_validate(raw)
    postgres_host = _host_for_this_process(settings.postgres.host)
    redis_host = _host_for_this_process(settings.redis.host)
    if postgres_host == settings.postgres.host and redis_host == settings.redis.host:
        return settings
    return settings.model_copy(
        update={
            "postgres": settings.postgres.model_copy(update={"host": postgres_host}),
            "redis": settings.redis.model_copy(update={"host": redis_host}),
        }
    )


@lru_cache
def get_settings() -> Settings:
    env = os.environ.get("ADPILOT_ENV", "dev").strip().lower() or "dev"
    if env not in {"dev", "prod"}:
        raise RuntimeError("ADPILOT_ENV 只允许 dev 或 prod")
    path = repo_root() / "deployment" / f"{env}.yaml"
    if not path.is_file():
        raise RuntimeError(f"缺少配置文件：{path}")
    return load_yaml(path)
