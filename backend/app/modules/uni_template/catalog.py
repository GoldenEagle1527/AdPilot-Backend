"""给全域漫剧机器人用的线上目录。

模板查 delivery_template 里未删除的全域行。剧场平台还没有来源，缺失时拒绝，不写假平台。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.modules.uni_template.crud import alive_uni_template_id_stmt


class DatabaseUniRobotCatalog:
    """UniRobotCatalog 的线上实现。模板打真实表，平台一律失败关闭。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def require_template(self, template_id: int) -> int:
        """未删除的全域模板才交回原样 id。标准模板和已删行都当不存在。"""
        result = await self._session.execute(alive_uni_template_id_stmt(template_id))
        if result.scalar_one_or_none() is None:
            raise ApiError(400, "全域模板不存在")
        return template_id

    async def require_platform(self, platform_id: int) -> int:
        """剧场平台还没有给机器人用的来源。缺来源就拒绝，不查剧场表，也不写假平台。"""
        del platform_id
        raise ApiError(400, "剧场平台不存在")
