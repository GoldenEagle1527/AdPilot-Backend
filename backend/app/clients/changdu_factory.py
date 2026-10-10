"""按 oceanengine.mock 选常读客户端。请求处理函数不要 import 本文件。"""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings


def promotion_client() -> Any:
    """mock 用假客户端，否则用会发 HTTP 的常读客户端。"""
    if get_settings().oceanengine.mock:
        from app.clients.fake_changdu import FakeChangduClient

        return FakeChangduClient()
    from app.clients.changdu import ChangduClient

    return ChangduClient()
