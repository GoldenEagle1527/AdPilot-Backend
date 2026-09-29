"""常读调用失败的钉钉通知。"""

from __future__ import annotations

from contextlib import suppress

import httpx

from app.notify.dingtalk import DingTalkWebhook, NotifySendError


class ChangduNotify:
    """常读调用失败时推钉钉。钉钉没发出去也不抛，不能盖住原来的常读错误。"""

    def __init__(self, webhook: DingTalkWebhook) -> None:
        """绑定一条钉钉通道。"""
        self._webhook = webhook

    async def _push(self, content: str) -> None:
        """推一条，钉钉失败吞掉。"""
        with suppress(NotifySendError, httpx.HTTPError):
            await self._webhook.push(content)

    async def sync_failed(self, message: str) -> None:
        """通知常读短剧列表拉取失败。"""
        await self._push(f"常读短剧列表拉取失败：{message}")

    async def promotion_failed(self, book_name: str, book_id: int, message: str) -> None:
        """通知一部剧的推广链重试用完仍拉取失败。"""
        await self._push(f"常读推广链拉取失败：{book_name}（book_id={book_id}）{message}")
