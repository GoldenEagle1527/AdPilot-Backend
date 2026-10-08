"""全域漫剧机器人用的外部目录。

业务只收下不透明的模板 id 和平台 id。目录里有哪些模板、哪些剧场平台，由调用方注入的实现回答。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class UniRobotCatalog(Protocol):
    """确认全域批量模板和剧场平台存在，并交回原样的 id。"""

    async def require_template(self, template_id: int) -> int:
        """全域批量模板必须存在。返回交给规则保存的模板 id。"""

    async def require_platform(self, platform_id: int) -> int:
        """剧场平台必须存在。返回交给规则保存的平台 id。"""
