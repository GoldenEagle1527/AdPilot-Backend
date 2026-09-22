"""漫剧库列表，以及常读短剧拉取落库。"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Awaitable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, NoReturn

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import ChangduSettings, get_settings
from app.core.pagination import PageParams, page_data
from app.core.times import BEIJING, beijing_iso
from app.modules.material.crud import insert_missing_series, page_series
from app.modules.material.model import ManhuaSeries
from app.modules.material.schema import ManhuaSeriesQuery
from app.notify.changdu import ChangduNotify
from app.notify.dingtalk import DingTalkWebhook, NotifySendError


def to_item(row: ManhuaSeries) -> dict[str, Any]:
    """把落库行收成列表项。部门本轮没有列，恒为 null。"""
    return {
        "id": str(row.id),
        "playlet_id": str(row.playlet_id),
        "book_id": str(row.book_id),
        "category_text": row.category_text,
        "tab_text": row.tab_text,
        "thumb_url": row.thumb_url,
        "book_name": row.book_name,
        "episode_amount": row.episode_amount,
        "department_name": None,
        "publish_status": row.publish_status,
        "delivery_status": row.delivery_status,
        "publish_time": row.publish_time,
        "estimate_publish_time": row.estimate_publish_time,
        "create_time": row.create_time,
        "collected_at": beijing_iso(row.collected_at),
        "douyin_nick_name": row.douyin_nick_name,
    }


async def list_manhua_series(session: AsyncSession, query: ManhuaSeriesQuery) -> dict[str, Any]:
    """按查询条件分页列出未删除漫剧。传入部门则空列表。"""
    params = PageParams(page=query.page, page_size=query.page_size)
    if query.department_id and query.department_id.strip():
        return page_data([], 0, params)
    filters = [ManhuaSeries.is_deleted == 0]
    if query.tab_text:
        filters.append(ManhuaSeries.tab_text == query.tab_text)
    name = (query.book_name or "").strip()
    if name:
        escaped = name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        filters.append(ManhuaSeries.book_name.ilike(f"%{escaped}%", escape="\\"))
    if query.estimate_publish_time_from is not None:
        filters.append(ManhuaSeries.estimate_publish_time >= query.estimate_publish_time_from)
    if query.estimate_publish_time_to is not None:
        filters.append(ManhuaSeries.estimate_publish_time <= query.estimate_publish_time_to)
        filters.append(ManhuaSeries.estimate_publish_time != "")
    if query.collected_at_from is not None:
        filters.append(ManhuaSeries.collected_at >= query.collected_at_from)
    if query.collected_at_to is not None:
        filters.append(ManhuaSeries.collected_at <= query.collected_at_to)
    if query.publish_status is not None:
        filters.append(ManhuaSeries.publish_status == query.publish_status)
    if query.listed_today is not None:
        today = datetime.now(BEIJING).date()
        start = today.isoformat()
        end = (today + timedelta(days=1)).isoformat()
        on_today = (ManhuaSeries.publish_time >= start) & (ManhuaSeries.publish_time < end)
        filters.append(on_today if query.listed_today else ~on_today)
    if query.episode_amount_min is not None:
        filters.append(ManhuaSeries.episode_amount >= query.episode_amount_min)
    if query.episode_amount_max is not None:
        filters.append(ManhuaSeries.episode_amount <= query.episode_amount_max)
    rows, total = await page_series(session, filters, offset=params.offset, limit=params.page_size)
    return page_data([to_item(row) for row in rows], total, params)


class ChangduError(RuntimeError):
    """常读 OpenAPI 调用失败。"""


@dataclass(frozen=True)
class AwemeSeriesPage:
    """常读端原生短剧/漫剧列表的一页。"""

    total: int
    data: list[dict[str, Any]]


class ChangduClient:
    """按常读签名调用端原生短剧/漫剧列表。"""

    def __init__(
        self,
        settings: ChangduSettings | None = None,
        client: httpx.AsyncClient | None = None,
        notify: ChangduNotify | None = None,
    ) -> None:
        """缺省从 deployment yaml 读常读和钉钉配置。传入的 httpx 客户端由调用方关闭。"""
        if settings is None:
            loaded = get_settings()
            settings = loaded.changdu
            if notify is None:
                notify = ChangduNotify(DingTalkWebhook(loaded.dingtalk.webhook))
        self._settings = settings
        self._client = client
        self._notify = notify if notify is not None else ChangduNotify(DingTalkWebhook(""))

    def sign(self, ts: int, params: Mapping[str, object]) -> str:
        """按键名升序把参数值用竖线拼上，再与渠道、密钥、时间戳做 MD5。"""
        ordered = dict(sorted(params.items()))
        params_value = "".join(f"{value}|" for value in ordered.values())
        raw = f"{self._settings.distributor_id}{self._settings.secret_key}{ts}{params_value}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _aweme_series_params(
        self,
        page_index: int,
        page_size: int,
        query: str | None,
        gender: int | None,
        publish_status: int | None,
        sort_field: int | None,
        sort_type: int | None,
        start_time: str | None,
        end_time: str | None,
    ) -> dict[str, int | str]:
        """组装短剧列表查询参数。没传的筛选项不放进去，避免参与签名。"""
        params: dict[str, int | str] = {
            "distributor_id": self._settings.distributor_id,
            "page_index": page_index,
            "page_size": page_size,
        }
        optional: dict[str, int | str | None] = {
            "query": query,
            "gender": gender,
            "publish_status": publish_status,
            "sort_field": sort_field,
            "sort_type": sort_type,
            "start_time": start_time,
            "end_time": end_time,
        }
        for key, value in optional.items():
            if value is not None:
                params[key] = value
        return dict(sorted(params.items()))

    async def _raise_changdu(self, pending: Awaitable[str], cause: BaseException | None = None) -> NoReturn:
        """等对应通知发完，再抛出常读错误。"""
        try:
            message = await pending
        except NotifySendError as exc:
            raise ChangduError(exc.text) from (cause or exc.__cause__)
        raise ChangduError(message) from cause

    async def _parse_aweme_series_page(self, response: httpx.Response) -> AwemeSeriesPage:
        """先看 HTTP 状态码，再看业务 code；不是 200 都失败并推对应钉钉通知。"""
        if response.status_code != 200:
            await self._raise_changdu(self._notify.http_failed(response.status_code))
        try:
            body = response.json()
        except ValueError as exc:
            await self._raise_changdu(self._notify.not_json(response.status_code), exc)
        if not isinstance(body, dict):
            await self._raise_changdu(self._notify.not_object(response.status_code))
        if body.get("code") != 200:
            await self._raise_changdu(self._notify.business_code(body.get("code"), body.get("message")))
        data = body.get("data") or []
        if not isinstance(data, list):
            await self._raise_changdu(self._notify.data_not_list())
        return AwemeSeriesPage(total=int(body.get("total") or 0), data=data)

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
        """按常读签名拉取端原生短剧/漫剧列表一页。缺省页码 0、每页 20。"""
        stamp = int(time.time()) if ts is None else ts
        params = self._aweme_series_params(
            page_index,
            page_size,
            query,
            gender,
            publish_status,
            sort_field,
            sort_type,
            start_time,
            end_time,
        )
        headers = {
            "header-sign": self.sign(stamp, params),
            "header-ts": str(stamp),
        }
        url = self._settings.base_url
        if self._client is None:
            async with httpx.AsyncClient(timeout=30) as http:
                response = await http.get(url, params=params, headers=headers)
        else:
            response = await self._client.get(url, params=params, headers=headers)
        return await self._parse_aweme_series_page(response)


def tab_text_from_price(single_price: object) -> str:
    """单价能解析且大于 0 为 IAP，否则为 IAA。"""
    text = "" if single_price is None else str(single_price).strip()
    try:
        charged = float(text) > 0
    except ValueError:
        charged = False
    return "IAP" if charged else "IAA"


def _as_int(value: object) -> int:
    """把常读数字收成 int，空或无法解析时为 0。"""
    if value is None or value == "":
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _as_str(value: object) -> str:
    """把常读字符串收成 str，缺省为空串。"""
    if value is None:
        return ""
    return str(value)


def fields_from_item(item: dict[str, Any]) -> dict[str, Any]:
    """把常读一条短剧收成漫剧表字段。题材进 category_text，页签由单价判断。"""
    price = _as_str(item.get("single_price"))
    delivery = item.get("delivery_status")
    return {
        "thumb_url": _as_str(item.get("thumb_url")),
        "book_id": _as_int(item.get("book_id")),
        "playlet_id": _as_int(item.get("playlet_id")),
        "book_name": _as_str(item.get("book_name")),
        "episode_amount": _as_int(item.get("episode_amount")),
        "gender": _as_int(item.get("gender")),
        "category_text": _as_str(item.get("category_text")),
        "tab_text": tab_text_from_price(price),
        "publish_status": _as_int(item.get("publish_status")),
        "publish_time": _as_str(item.get("publish_time")),
        "estimate_publish_time": _as_str(item.get("estimate_publish_time")),
        "permission_status": _as_int(item.get("permission_status")),
        "create_time": _as_str(item.get("create_time")),
        "douyin_nick_name": _as_str(item.get("douyin_nick_name")),
        "single_price": price,
        "abstract": _as_str(item.get("abstract")),
        "delivery_status": delivery if isinstance(delivery, bool) else False,
    }


def collapse_by_playlet_book(items: list[dict[str, Any]]) -> dict[tuple[int, str], dict[str, Any]]:
    """按 playlet_id + book_name 去重。同一页后者覆盖前者；没有剧名的丢掉。"""
    incoming: dict[tuple[int, str], dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        fields = fields_from_item(item)
        book_name = fields["book_name"]
        if not book_name:
            continue
        incoming[(fields["playlet_id"], book_name)] = fields
    return incoming


async def save_aweme_series(session: AsyncSession, items: list[dict[str, Any]]) -> int:
    """把常读一页短剧去重后插入漫剧表。表里已有的跳过。返回插入条数。"""
    return await insert_missing_series(session, collapse_by_playlet_book(items))
