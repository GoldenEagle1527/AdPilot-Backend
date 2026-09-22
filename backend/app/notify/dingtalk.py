"""钉钉自定义机器人通道。只负责把文本发出去。"""

from __future__ import annotations

import httpx

# 钉钉机器人自定义关键词。所有通知发出前都会带上。
KEYWORD = "AdPilot"


def with_keyword(content: str) -> str:
    """给任意通知正文加上全局关键词。"""
    text = content.strip()
    if text.startswith(KEYWORD):
        return text
    return f"{KEYWORD} {text}"


class DingTalkError(RuntimeError):
    """钉钉机器人推送失败。"""


class NotifySendError(Exception):
    """通知正文已写好，但钉钉没发出去。"""

    def __init__(self, text: str) -> None:
        self.text = text
        super().__init__(text)


class DingTalkWebhook:
    """把文本推到钉钉自定义机器人 webhook。"""

    def __init__(self, webhook: str = "", client: httpx.AsyncClient | None = None) -> None:
        """保存 webhook。传入的 httpx 客户端由调用方关闭。"""
        self._webhook = webhook.strip()
        self._client = client

    async def push_text(self, content: str) -> None:
        """推送一段文本。没配 webhook 则不发。"""
        if not self._webhook:
            return
        payload = {"msgtype": "text", "text": {"content": with_keyword(content)}}
        if self._client is None:
            async with httpx.AsyncClient(timeout=10) as http:
                response = await http.post(self._webhook, json=payload)
        else:
            response = await self._client.post(self._webhook, json=payload)
        try:
            body = response.json()
        except ValueError as exc:
            raise DingTalkError(f"钉钉返回不是 JSON：HTTP {response.status_code}") from exc
        errcode = body.get("errcode") if isinstance(body, dict) else None
        errmsg = body.get("errmsg") if isinstance(body, dict) else ""
        if response.status_code != 200 or errcode != 0:
            raise DingTalkError(f"钉钉通知失败：HTTP {response.status_code} errcode={errcode} {errmsg}")

    async def push(self, content: str) -> str:
        """推送正文并原样返回。钉钉失败时仍带回正文，供调用方抛业务错误。"""
        try:
            await self.push_text(content)
        except DingTalkError as exc:
            raise NotifySendError(content) from exc
        return content
