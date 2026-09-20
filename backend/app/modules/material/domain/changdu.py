from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

import httpx

from app.core.config import ChangduSettings
from app.modules.material.domain.times import BEIJING

logger = logging.getLogger(__name__)

AWEME_SERIES_PATH = "/novelsale/openapi/content/aweme_series/list/v1/"
PAGE_SIZE = 20
PAGE_GAP_SECONDS = 0.35


class ChangduError(RuntimeError):
    pass


@dataclass(frozen=True)
class AwemeSeriesRecord:
    thumb_url: str
    book_id: int
    playlet_id: int
    book_name: str
    episode_amount: int
    gender: int
    category_text: str
    publish_status: int
    publish_time: str
    estimate_publish_time: str
    permission_status: int
    create_time: str
    douyin_nick_name: str
    single_price: str
    abstract: str
    delivery_status: bool


class SeriesPageClient(Protocol):
    async def fetch_page(
        self,
        *,
        start_time: str,
        end_time: str,
        page_index: int,
        page_size: int,
    ) -> tuple[int, list[AwemeSeriesRecord]]: ...


def sign_get(distributor_id: str, secret_key: str, ts: int, params: dict[str, Any]) -> str:
    ordered = dict(sorted(params.items(), key=lambda item: str(item[0])))
    values = "".join(f"{v}|" for v in ordered.values())
    raw = f"{distributor_id}{secret_key}{ts}{values}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def sync_window(now: datetime | None = None) -> tuple[str, str]:
    """常读只要日期。带时分秒会 4000 参数错误；按北京日历日拉当天。"""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    day = current.astimezone(BEIJING).date().isoformat()
    return day, day


def _as_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value in (1, "1", "true", "True"):
        return True
    return False


def parse_record(raw: dict[str, Any]) -> AwemeSeriesRecord:
    return AwemeSeriesRecord(
        thumb_url=_as_str(raw.get("thumb_url")),
        book_id=_as_int(raw.get("book_id")),
        playlet_id=_as_int(raw.get("playlet_id")),
        book_name=_as_str(raw.get("book_name")),
        episode_amount=_as_int(raw.get("episode_amount")),
        gender=_as_int(raw.get("gender")),
        category_text=_as_str(raw.get("category_text")),
        publish_status=_as_int(raw.get("publish_status")),
        publish_time=_as_str(raw.get("publish_time")),
        estimate_publish_time=_as_str(raw.get("estimate_publish_time")),
        permission_status=_as_int(raw.get("permission_status")),
        create_time=_as_str(raw.get("create_time")),
        douyin_nick_name=_as_str(raw.get("douyin_nick_name")),
        single_price=_as_str(raw.get("single_price")),
        abstract=_as_str(raw.get("abstract")),
        delivery_status=_as_bool(raw.get("delivery_status")),
    )


class ChangduAwemeClient:
    def __init__(self, settings: ChangduSettings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client

    def configured(self) -> bool:
        return bool(self._settings.distributor_id.strip() and self._settings.secret_key.strip())

    async def fetch_page(
        self,
        *,
        start_time: str,
        end_time: str,
        page_index: int,
        page_size: int,
    ) -> tuple[int, list[AwemeSeriesRecord]]:
        params: dict[str, Any] = {
            "distributor_id": int(self._settings.distributor_id),
            "end_time": end_time,
            "page_index": page_index,
            "page_size": page_size,
            "start_time": start_time,
        }
        ts = int(datetime.now(timezone.utc).timestamp())
        sign = sign_get(
            str(self._settings.distributor_id),
            self._settings.secret_key,
            ts,
            params,
        )
        url = f"{self._settings.base_url.rstrip('/')}{AWEME_SERIES_PATH}"
        headers = {"header-ts": str(ts), "header-sign": sign}
        owns = self._client is None
        client = self._client or httpx.AsyncClient(timeout=30.0)
        try:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            body = response.json()
        finally:
            if owns:
                await client.aclose()
        code = body.get("code")
        if code not in (0, 200, "0", "200"):
            raise ChangduError(f"常读返回 {code}: {body.get('message')}")
        total = _as_int(body.get("total"))
        rows = body.get("data") or []
        if not isinstance(rows, list):
            raise ChangduError("常读 data 不是列表")
        return total, [parse_record(row) for row in rows if isinstance(row, dict)]
