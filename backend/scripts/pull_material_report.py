"""后台拉取近 30 天素材报表。

在 backend/ 下执行：python scripts/pull_material_report.py

只 GET 自定义报表。不创建、不修改、不暂停、不删除巨量对象。
假客户端的样例行不写入 oe_material_report。
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import dispose_engine, get_session, init_engine
from app.modules.oceanengine.material_report import pull_material_report_30d


async def _main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    init_engine()
    written = 0
    try:
        async for session in get_session():
            written = await pull_material_report_30d(session)
            break
    finally:
        await dispose_engine()
    print(f"rows_written={written}")
    return written


if __name__ == "__main__":
    asyncio.run(_main())
