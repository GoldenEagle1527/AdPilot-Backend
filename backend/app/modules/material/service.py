"""漫剧库列表，以及常读短剧拉取落库。"""

from __future__ import annotations

import io
from datetime import datetime, timedelta
from typing import Any

from openpyxl import Workbook
from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageParams, page_data
from app.core.times import BEIJING, beijing_iso, beijing_stamp, parse_beijing_stamp
from app.modules.material.crud import insert_missing_series, list_series, page_series
from app.modules.material.model import ManhuaSeries
from app.modules.material.schema import ManhuaSeriesQuery


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
        "estimate_publish_time": beijing_stamp(row.estimate_publish_time),
        "create_time": row.create_time,
        "collected_at": beijing_iso(row.collected_at),
        "douyin_nick_name": row.douyin_nick_name,
    }


def series_filters(query: ManhuaSeriesQuery) -> list[ColumnElement[bool]]:
    """列表和导出共用的筛选。"""
    filters: list[ColumnElement[bool]] = [ManhuaSeries.is_deleted == 0]
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
    return filters


async def list_manhua_series(session: AsyncSession, query: ManhuaSeriesQuery) -> dict[str, Any]:
    """按查询条件分页列出未删除漫剧。"""
    params = PageParams(page=query.page, page_size=query.page_size)
    filters = series_filters(query)
    rows, total = await page_series(session, filters, offset=params.offset, limit=params.page_size)
    return page_data([to_item(row) for row in rows], total, params)


_PUBLISH_STATUS = {1: "未发布", 2: "已发布", 3: "已下架"}

_EXPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("book_name", "短剧名称"),
    ("episode_amount", "集数"),
    ("publish_status", "发布状态"),
    ("estimate_publish_time", "预估投放时间"),
    ("listed_today", "是否当天上架"),
    ("publish_time", "发布时间"),
    ("create_time", "创建时间"),
    ("collected_at", "采集时间"),
    ("playlet_id", "抖音id"),
    ("douyin_nick_name", "抖音名"),
)

def _listed_today(publish_time: object) -> str:
    """发布时间落在北京今天则为是。"""
    text = "" if publish_time is None else str(publish_time)
    today = datetime.now(BEIJING).date().isoformat()
    return "是" if text[:10] == today else "否"


def _plain_stamp(value: object) -> str:
    """采集时间收成 YYYY-MM-DD HH:MM:SS。"""
    text = "" if value is None else str(value)
    if "T" not in text:
        return text
    return text.replace("T", " ").split("+", 1)[0].split("Z", 1)[0][:19]


def export_cells(item: dict[str, Any]) -> list[str]:
    """把一条列表项收成导出行。发布状态和是否当天上架写成中文，抖音id 用专辑 ID。"""
    cells: list[str] = []
    for key, _label in _EXPORT_COLUMNS:
        if key == "listed_today":
            cells.append(_listed_today(item.get("publish_time")))
            continue
        value = item.get(key)
        if key == "publish_status":
            cells.append(_PUBLISH_STATUS.get(int(value), "" if value is None else str(value)))
        elif key == "collected_at":
            cells.append(_plain_stamp(value))
        elif value is None:
            cells.append("")
        else:
            cells.append(str(value))
    return cells


def rows_to_xlsx(headers: list[str], rows: list[list[str]]) -> bytes:
    """表头加文本行打成 xlsx。值已是字符串，大整数不会被 Excel 改成科学计数。"""
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.title = "漫剧库"
    sheet.append(headers)
    for line in rows:
        sheet.append(line)
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


async def export_manhua_series(session: AsyncSession, query: ManhuaSeriesQuery) -> bytes:
    """按列表相同筛选导出全部匹配行。page、page_size 不参与。

    ponytail: 匹配行一次读进内存再打成 xlsx。到十万行再改成分批写入或加上限。
    """
    filters = series_filters(query)
    rows = await list_series(session, filters)
    headers = [label for _key, label in _EXPORT_COLUMNS]
    return rows_to_xlsx(headers, [export_cells(to_item(row)) for row in rows])


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
        "estimate_publish_time": parse_beijing_stamp(item.get("estimate_publish_time")),
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
