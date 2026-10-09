from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.core.access_log import api_log_config, apply_access_log
from app.core.auth import router as auth_router
from app.core.config import get_settings
from app.core.cors import apply_cors
from app.core.db import dispose_engine, get_session, init_engine
from app.core.envelope import register_exception_handlers
from app.core.health import router as health_router
from app.core.redis_client import close_redis, init_redis
from app.modules.file import router as file_router
from app.modules.material import router as material_router
from app.modules.material_title import router as material_title_router
from app.modules.material_video import router as material_video_router
from app.modules.oceanengine import router as oceanengine_router
from app.modules.standard_delivery import router as standard_delivery_router
from app.modules.standard_robot import router as standard_robot_router
from app.modules.system_admin import router as system_admin_router
from app.modules.theater import router as theater_router
from app.modules.uni_native_auto_run import router as uni_native_auto_run_router
from app.modules.uni_native_task import router as uni_native_task_router
from app.modules.uni_robot import router as uni_robot_router
from app.modules.uni_template import router as uni_template_router

logger = logging.getLogger("adpilot")
_RULE_INTERVAL_SECONDS = 60


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """启动时接库和 Redis。mock 时选定假客户端并写一次巨量种子。约每分钟跑到点规则。"""
    settings = get_settings()
    init_engine(settings)
    init_redis(settings)
    from app.modules.oceanengine.client_factory import install_ocean_client_for_settings

    install_ocean_client_for_settings(settings)
    if settings.oceanengine.mock:
        await _seed_oceanengine()
    ticker = asyncio.create_task(_due_rules_loop())
    try:
        yield
    finally:
        ticker.cancel()
        try:
            await ticker
        except asyncio.CancelledError:
            pass
        await close_redis()
        await dispose_engine()


async def _due_rules_loop() -> None:
    """约每分钟看一次到点的标准自动规则和漫剧机器人规则。"""
    from app.modules.delivery_runner.loop import run_due_rules

    while True:
        try:
            async for session in get_session():
                await run_due_rules(session)
                break
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("到点规则本轮失败")
        await asyncio.sleep(_RULE_INTERVAL_SECONDS)


async def _seed_oceanengine() -> None:
    """幂等写入巨量种子。平台表为空时再写入番茄和鸥溪。只在启动且 mock 时调用。"""
    from app.modules.account.seed import ensure_oceanengine_seed
    from scripts.seed_theater_platforms import ensure_theater_platforms

    async for session in get_session():
        await ensure_oceanengine_seed(session)
        await ensure_theater_platforms(session)
        await session.commit()
        break


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
    app.include_router(file_router)
    app.include_router(material_router)
    app.include_router(material_title_router)
    app.include_router(material_video_router)
    app.include_router(oceanengine_router)
    app.include_router(theater_router)
    app.include_router(uni_robot_router)
    app.include_router(uni_template_router)
    app.include_router(uni_native_task_router)
    app.include_router(uni_native_auto_run_router)
    app.include_router(standard_delivery_router)
    app.include_router(standard_robot_router)
    return app


app = create_app()


def run() -> None:
    """用配置里的 host/port 起 uvicorn。"""
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.listen_host,
        port=settings.listen_port,
        log_config=api_log_config(),
    )


if __name__ == "__main__":
    run()
