"""在 backend/ 下执行：python scripts/seed_theater_platforms.py

往脚本里写死的库插入番茄（id=1）、鸥溪（id=22）两条剧场平台。已有同 id / 名称 / 平台码则跳过。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.dialects.postgresql import insert

from app.core.config import get_settings
from app.core.db import dispose_engine, get_session, init_engine
from app.modules.theater.model import TheaterPlatform

_POSTGRES = {
    "host": "192.168.111.40",
    "port": 5432,
    "database": "ad_pilot",
    "user": "root",
    "password": "ocsaas123456",
}

_ROWS = [
    {"id": 1, "name": "番茄", "code": "1011", "sort_order": 1},
    {"id": 22, "name": "鸥溪", "code": "4504", "sort_order": 2},
]


def _bind_database() -> None:
    """固定连到脚本里的库，不跟 deployment yaml 的 postgres 走。"""
    settings = get_settings()
    postgres = settings.postgres.model_copy(update=_POSTGRES)
    init_engine(settings.model_copy(update={"postgres": postgres}))


async def load_platforms() -> None:
    """把两条固定平台写入 theater_platforms。"""
    async for session in get_session():
        result = await session.execute(
            insert(TheaterPlatform).values(_ROWS).on_conflict_do_nothing().returning(TheaterPlatform.id)
        )
        inserted = result.scalars().all()
        await session.commit()
        print(f"剧场平台：新插入 {len(inserted)} 条 {inserted}（已存在的已跳过）")


def main() -> None:
    """命令行入口：连上脚本里的库并写入两条平台。"""

    async def _run() -> None:
        try:
            _bind_database()
            await load_platforms()
        finally:
            await dispose_engine()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
