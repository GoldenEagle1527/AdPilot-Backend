"""把日表行收成接口要的一行。只加已经算好的日数，不再查小时表和中台。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from app.modules.report.schema import ManhuaQuery
from app.modules.report.service import (
    MANHUA_BASE,
    SEP,
    UNI_MONEY,
    ZERO,
    _iso,
    drama_age,
    manhua_metrics,
    uni_metrics,
)


def _dec(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def _names(values: list[str] | None) -> str:
    return SEP.join(sorted({item for item in values or [] if item}))


def _union_text(parts: list[list[str]]) -> list[str]:
    found: set[str] = set()
    for part in parts:
        found.update(item for item in part or [] if item)
    return sorted(found)


def _union_int(parts: list[list[int]]) -> list[int]:
    found: set[int] = set()
    for part in parts:
        found.update(int(item) for item in part or [])
    return sorted(found)


def fold_manhua_dramas(rows: list[dict[str, Any]], query: ManhuaQuery, user_id: int | None) -> list[dict[str, Any]]:
    """区间内同一部剧（付费再加面板）合成一行。user_id 为空时不过滤投手。"""
    groups: dict[tuple[int, str], dict[str, Any]] = {}
    for row in rows:
        key = (int(row["series_id"]), str(row.get("panel_key") or ""))
        group = groups.get(key)
        if group is None:
            group = {
                "row": row,
                "sums": {},
                "names": [],
                "depts": [],
                "bids": [],
                "panels": [],
                "costed": [],
                "ids": [],
            }
            groups[key] = group
        for name in MANHUA_BASE:
            group["sums"][name] = group["sums"].get(name, ZERO) + _dec(row.get(name))
        group["names"].append(list(row.get("pitcher_names") or []))
        group["depts"].append(list(row.get("department_names") or []))
        group["bids"].append(list(row.get("bid_types") or []))
        group["panels"].append(list(row.get("panel_names") or []))
        group["costed"].append(list(row.get("costed_promotion_ids") or []))
        group["ids"] = _union_int([group["ids"], list(row.get("pitcher_ids") or [])])
    out: list[dict[str, Any]] = []
    for (series_id, panel_key), group in groups.items():
        pitcher_ids = group["ids"]
        if user_id is not None and user_id not in pitcher_ids:
            continue
        head = group["row"]
        names = _union_text(group["names"])
        depts = _union_text(group["depts"])
        bids = _union_text(group["bids"])
        panels = _union_text(group["panels"])
        if query.series_id and series_id not in query.series_id:
            continue
        if query.series_name and query.series_name.strip() not in str(head.get("book_name") or ""):
            continue
        if query.drama_type and head.get("drama_type") not in query.drama_type:
            continue
        if query.channel and head.get("channel") not in query.channel:
            continue
        if query.bid_type and set(bids).isdisjoint(query.bid_type):
            continue
        if query.panel and panel_key not in query.panel and set(panels).isdisjoint(query.panel):
            continue
        if query.team and set(depts).isdisjoint(query.team):
            continue
        if query.pitcher and set(names).isdisjoint(query.pitcher):
            continue
        age = drama_age(head.get("publish_date"), query.date_start, query.date_end)
        if query.drama_age and age not in query.drama_age:
            continue
        panel = panel_key if query.charge_mode == "IAP" else SEP.join(panels)
        out.append(
            {
                "series_id": series_id,
                "book_name": head.get("book_name") or "",
                "media": "巨量",
                "drama_type": head.get("drama_type") or "",
                "channel": head.get("channel") or "",
                "bid_type": SEP.join(bids),
                "panel": panel,
                "drama_age": age,
                "teams": SEP.join(depts),
                "pitchers": SEP.join(names),
                "promotion_with_cost_count": len(_union_int(group["costed"])),
                **manhua_metrics(group["sums"]),
            }
        )
    return out


def fold_manhua_projects(rows: list[dict[str, Any]], query: ManhuaQuery, user_id: int | None) -> list[dict[str, Any]]:
    """区间内同一个项目合成一行。user_id 为空时留下全部投手。"""
    return _fold_owned(rows, query, user_id, "project_id")


def fold_manhua_promotions(rows: list[dict[str, Any]], query: ManhuaQuery, user_id: int | None) -> list[dict[str, Any]]:
    """区间内同一条广告合成一行。user_id 为空时留下全部投手。"""
    return _fold_owned(rows, query, user_id, "promotion_id")


def _fold_owned(rows: list[dict[str, Any]], query: ManhuaQuery, user_id: int | None, key_name: str) -> list[dict[str, Any]]:
    groups: dict[int, dict[str, Any]] = {}
    for row in rows:
        if user_id is not None and int(row.get("pitcher_id") or 0) != user_id:
            continue
        key = int(row[key_name])
        group = groups.get(key)
        if group is None:
            group = {"row": row, "sums": {}, "first": row.get("first_cost_time")}
            groups[key] = group
        for name in MANHUA_BASE:
            group["sums"][name] = group["sums"].get(name, ZERO) + _dec(row.get(name))
        first = row.get("first_cost_time")
        if first and (group["first"] is None or str(first) < str(group["first"])):
            group["first"] = first
    out: list[dict[str, Any]] = []
    for key, group in groups.items():
        head = group["row"]
        if query.series_id and int(head.get("series_id") or 0) not in query.series_id:
            continue
        if query.series_name and query.series_name.strip() not in str(head.get("book_name") or ""):
            continue
        if query.drama_type and head.get("drama_type") not in query.drama_type:
            continue
        if query.channel and head.get("channel") not in query.channel:
            continue
        if query.bid_type and head.get("bid_type") not in query.bid_type:
            continue
        if query.panel and head.get("panel") not in query.panel:
            continue
        if query.team and head.get("department_name") not in query.team:
            continue
        if query.pitcher and head.get("pitcher_name") not in query.pitcher:
            continue
        age = drama_age(head.get("publish_date"), query.date_start, query.date_end)
        if query.drama_age and age not in query.drama_age:
            continue
        item = {
            "series_id": int(head.get("series_id") or 0),
            "book_name": head.get("book_name") or "",
            "pitcher": head.get("pitcher_name") or "",
            "team": head.get("department_name") or "",
            "project_budget": None if head.get("project_budget") is None else round(float(head["project_budget"]), 2),
            "roi_goal": None if head.get("roi_goal") is None else round(float(head["roi_goal"]), 3),
            "created_at": head.get("created_at") if isinstance(head.get("created_at"), str) else _iso(head.get("created_at")),
            "first_cost_time": group["first"],
            **manhua_metrics(group["sums"]),
        }
        if key_name == "project_id":
            item["project_id"] = key
            item["project_name"] = head.get("project_name") or ""
        else:
            item["promotion_id"] = key
            item["promotion_name"] = head.get("promotion_name") or ""
            item["project_id"] = int(head.get("project_id") or 0)
            item["project_name"] = head.get("project_name") or ""
        out.append(item)
    return out


def uni_row_metrics(row: dict[str, Any]) -> dict[str, Any]:
    """一天的全域可加字段转成对外指标。固定为 0 的列在这里补。"""
    sums = {name: _dec(row.get(name)) for name in UNI_MONEY}
    sums["new_project_count"] = _dec(row.get("new_project_count"))
    metrics = uni_metrics(sums)
    metrics["new_project_with_cost_count"] = 0
    metrics["spending_project_count"] = 0
    metrics["spending_advertiser_count"] = 0
    return metrics
