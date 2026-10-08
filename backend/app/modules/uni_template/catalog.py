"""给全域漫剧机器人用的线上目录。

模板查 delivery_template 里未删除的全域行。剧场平台查未删除的 theater_platforms。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.modules.theater.model import TheaterPlatform
from app.modules.uni_template.crud import alive_uni_template_id_stmt


class DatabaseUniRobotCatalog:
    """UniRobotCatalog 的线上实现。模板和平台都打真实表，不写假平台。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def require_template(self, template_id: int) -> int:
        """未删除的全域模板才交回原样 id。标准模板和已删行都当不存在。"""
        result = await self._session.execute(alive_uni_template_id_stmt(template_id))
        if result.scalar_one_or_none() is None:
            raise ApiError(400, "全域模板不存在")
        return template_id

    async def require_platform(self, platform_id: int) -> int:
        """未删除的剧场平台才交回原样 id。未知 id 拒绝。"""
        result = await self._session.execute(
            select(TheaterPlatform.id).where(
                TheaterPlatform.id == platform_id,
                TheaterPlatform.is_deleted == 0,
            )
        )
        if result.scalar_one_or_none() is None:
            raise ApiError(400, "剧场平台不存在")
        return platform_id
