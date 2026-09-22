"""常读短剧列表的钉钉错误通知。一种失败一条文案。"""

from __future__ import annotations

from app.notify.dingtalk import DingTalkWebhook


class ChangduNotify:
    """常读列表失败时按错误类型推钉钉。"""

    def __init__(self, webhook: DingTalkWebhook) -> None:
        """绑定一条钉钉通道。"""
        self._webhook = webhook

    async def http_failed(self, status_code: int) -> str:
        """通知常读列表 HTTP 状态不是 200。"""
        return await self._webhook.push(f"常读短剧列表 HTTP 失败：{status_code}")

    async def not_json(self, status_code: int) -> str:
        """通知常读返回体不是 JSON。"""
        return await self._webhook.push(f"常读返回不是 JSON：HTTP {status_code}")

    async def not_object(self, status_code: int) -> str:
        """通知常读 JSON 不是对象。"""
        return await self._webhook.push(f"常读返回不是对象：HTTP {status_code}")

    async def business_code(self, code: object, message: object) -> str:
        """通知常读业务 code 不是 200。"""
        return await self._webhook.push(f"常读短剧列表失败：code={code} {message}")

    async def data_not_list(self) -> str:
        """通知常读 data 不是数组。"""
        return await self._webhook.push("常读短剧列表 data 不是数组")
