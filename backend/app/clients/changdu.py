"""常读 OpenAPI 客户端：签名、请求、统一校验返回。失败只抛 ChangduError，推不推钉钉由调用方决定。"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import ChangduSettings, get_settings

# 获取推广链接列表-v2 的 limit 最大 100
PROMOTION_PAGE_SIZE = 100


class ChangduError(RuntimeError):
    """常读 OpenAPI 调用失败。业务失败时正文是常读 message。"""


@dataclass(frozen=True)
class AwemeSeriesPage:
    """常读端原生短剧/漫剧列表的一页。"""

    total: int
    data: list[dict[str, Any]]


def checked_body(response: httpx.Response) -> dict[str, Any]:
    """HTTP 不是 200、不是 JSON 对象、业务 code 不是 200 都抛常读错误。"""
    if response.status_code != 200:
        raise ChangduError(f"常读 HTTP 失败：{response.status_code}")
    try:
        body = response.json()
    except ValueError as exc:
        raise ChangduError(f"常读返回不是 JSON：HTTP {response.status_code}") from exc
    if not isinstance(body, dict):
        raise ChangduError(f"常读返回不是对象：HTTP {response.status_code}")
    if body.get("code") != 200:
        raise ChangduError(str(body.get("message") or f"常读 code={body.get('code')}"))
    return body


class ChangduClient:
    """按常读签名调用 OpenAPI。"""

    def __init__(self, settings: ChangduSettings | None = None, client: httpx.AsyncClient | None = None) -> None:
        """缺省从 deployment yaml 读常读配置。传入的 httpx 客户端由调用方关闭。"""
        self._settings = settings or get_settings().changdu
        self._client = client

    def sign(self, ts: int, params: Mapping[str, object]) -> str:
        """按键名升序把参数值用竖线拼上，再与渠道、密钥、时间戳做 MD5。"""
        ordered = dict(sorted(params.items()))
        params_value = "".join(f"{value}|" for value in ordered.values())
        raw = f"{self._settings.distributor_id}{self._settings.secret_key}{ts}{params_value}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    async def _get(self, url: str, params: Mapping[str, object], ts: int | None) -> dict[str, Any]:
        """带签名 GET 一次，返回校验过的返回体。"""
        stamp = int(time.time()) if ts is None else ts
        headers = {"header-sign": self.sign(stamp, params), "header-ts": str(stamp)}
        if self._client is None:
            async with httpx.AsyncClient(timeout=30) as http:
                response = await http.get(url, params=params, headers=headers)
        else:
            response = await self._client.get(url, params=params, headers=headers)
        return checked_body(response)

    async def list_aweme_series(
        self,
        *,
        page_index: int = 0,
        page_size: int = 20,
        query: str | None = None,
        gender: int | None = None,
        publish_status: int | None = None,
        sort_field: int | None = None,
        sort_type: int | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        ts: int | None = None,
    ) -> AwemeSeriesPage:
        """拉取端原生短剧/漫剧列表一页。没传的筛选项不放进参数，避免参与签名。"""
        params: dict[str, int | str] = {
            "distributor_id": self._settings.distributor_id,
            "page_index": page_index,
            "page_size": page_size,
        }
        optional = {
            "query": query,
            "gender": gender,
            "publish_status": publish_status,
            "sort_field": sort_field,
            "sort_type": sort_type,
            "start_time": start_time,
            "end_time": end_time,
        }
        params.update({key: value for key, value in optional.items() if value is not None})
        body = await self._get(self._settings.base_url, params, ts)
        data = body.get("data") or []
        if not isinstance(data, list):
            raise ChangduError("常读短剧列表 data 不是数组")
        return AwemeSeriesPage(total=int(body.get("total") or 0), data=data)

    async def list_promotions(self, book_id: int, *, ts: int | None = None) -> list[dict[str, Any]]:
        """获取推广链接列表-v2：按 book_id 翻页拉全部推广链。没有更多或本页为空就停。"""
        items: list[dict[str, Any]] = []
        offset = 0
        while True:
            params = {
                "book_id": str(book_id),
                "distributor_id": self._settings.distributor_id,
                "limit": PROMOTION_PAGE_SIZE,
                "offset": offset,
            }
            body = await self._get(self._settings.promotion_list_url, params, ts)
            page = [item for item in body.get("result") or [] if isinstance(item, dict)]
            items.extend(page)
            if not page or not body.get("has_more"):
                return items
            offset = int(body.get("next_offset") or offset + PROMOTION_PAGE_SIZE)
