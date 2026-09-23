from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.core.access_log import apply_access_log
from app.core.auth import router as auth_router
from app.core.config import get_settings
from app.core.cors import apply_cors
from app.core.db import dispose_engine, init_engine
from app.core.envelope import register_exception_handlers
from app.core.health import router as health_router
from app.core.redis_client import close_redis, init_redis
from app.modules.material import router as material_router
from app.modules.material_title import router as material_title_router
from app.modules.system_admin import router as system_admin_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """启动时接库和 Redis，关掉时释放连接。"""
    settings = get_settings()
    init_engine(settings)
    init_redis(settings)
    yield
    await close_redis()
    await dispose_engine()


def create_app() -> FastAPI:
    """组装 FastAPI：信封、CORS、登录与各业务路由。"""
    settings = get_settings()
    app = FastAPI(
        title="AdPilot API",
        description="信封 `{ code, message, data }`。除 login/health/ready 外带 `Authorization: Bearer`。",
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    register_exception_handlers(app)
    apply_cors(app, settings)
    apply_access_log(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(system_admin_router)
    app.include_router(material_router)
    app.include_router(material_title_router)
    return app


app = create_app()


def run() -> None:
    """用配置里的 host/port 起 uvicorn。"""
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.listen_host,
        port=settings.listen_port,
    )


if __name__ == "__main__":
    run()
