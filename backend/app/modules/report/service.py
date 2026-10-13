"""报表行的拼装。只吃已经从快照和中台表读出来的数据，不碰库，也不调巨量。

行、权限、指标口径见 Plan/product/数据报表/口径.md。
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Iterable

from app.core.times import BEIJING, beijing_stamp
from app.modules.report.schema import MEDIA_OCEAN, ManhuaQuery

SEP = "、"
ZERO = Decimal("0")

MANHUA_MONEY = (
    "stat_cost",
    "stat_pay_amount",
    "attribution_game_in_app_ltv_1day",
    "attribution_game_in_app_ltv_8days",
    "attribution_micro_game_0d_ltv",
    "attribution_micro_game_7d_ltv",
)
MANHUA_COUNTS = ("show_cnt", "click_cnt", "convert_cnt", "active")
MANHUA_BASE = (*MANHUA_MONEY, *MANHUA_COUNTS)

UNI_MONEY = (
    "all_stat_cost_trend",
    "all_stat_total_cost_trend",
    "all_gmv_trend",
    "all_billing_gmv_0day_trend",
    "all_billing_gmv_24h_trend",
    "all_billing_gmv_3days_trend",
    "all_income_trend",
    "all_income_0day_trend",
    "all_pay_amount_income_trend",
    "all_micro_game_income_trend",
)
ZERO_COLUMNS = ("new_project_with_cost_count", "spending_project_count", "spending_advertiser_count")


@dataclass(frozen=True)
class ProjectLink:
    """中台里一个提交成功的巨量项目，以及它回得到的剧、投手、部门。"""

    project_id: int
    series_id: int
    book_name: str
    pitcher_id: int
    pitcher_name: str
    department_id: int | None
    department_name: str
    charge_mode: str = ""
    bid_panel: str = ""
    bid_type: str = ""
    drama_type: str = ""
    channel: str = ""
    publish_date: date | None = None
    created_at: datetime | None = None
    project_budget: Decimal | None = None
    roi_goal: Decimal | None = None
    stored: bool = True


@dataclass(frozen=True)
class PromotionLink:
    promotion_id: int
    project_id: int
    created_at: datetime | None = None


@dataclass
class ManhuaFact:
    """一条广告在所选区间内的合计。"""

    project_id: int
    promotion_id: int
    project_name: str = ""
    promotion_name: str = ""
    metrics: dict[str, Decimal] = field(default_factory=dict)
    first_cost_hour: str | None = None


@dataclass
class UniFact:
    """一个全域项目一天的合计。"""

    day: str
    project_id: int
    project_name: str = ""
    metrics: dict[str, Decimal] = field(default_factory=dict)


def ratio(numerator: Decimal | int, denominator: Decimal | int, places: int = 4) -> float:
    """分母为 0 时返回 0。"""
    if not denominator:
        return 0.0
    return round(float(Decimal(numerator) / Decimal(denominator)), places)


def _money(value: Decimal | int) -> float:
    return round(float(value), 2)


def _add(target: dict[str, Decimal], metrics: dict[str, Decimal], names: Iterable[str]) -> None:
    for name in names:
        target[name] = target.get(name, ZERO) + Decimal(metrics.get(name) or 0)


def manhua_metrics(sums: dict[str, Decimal]) -> dict[str, Any]:
    """累加指标转成对外字段。比率一律用合计后的分子分母算，不平均各行比率。"""
    cost = sums.get("stat_cost", ZERO)
    show = sums.get("show_cnt", ZERO)
    click = sums.get("click_cnt", ZERO)
    active = sums.get("active", ZERO)
    convert = sums.get("convert_cnt", ZERO)
    out: dict[str, Any] = {name: _money(sums.get(name, ZERO)) for name in MANHUA_MONEY}
    out.update({name: int(sums.get(name, ZERO)) for name in MANHUA_COUNTS})
    out["pay_amount_roi"] = ratio(sums.get("stat_pay_amount", ZERO), cost)
    out["attribution_game_in_app_roi_1day"] = ratio(sums.get("attribution_game_in_app_ltv_1day", ZERO), cost)
    out["attribution_game_in_app_roi_8days"] = ratio(sums.get("attribution_game_in_app_ltv_8days", ZERO), cost)
    out["attribution_micro_game_0d_roi"] = ratio(sums.get("attribution_micro_game_0d_ltv", ZERO), cost)
    out["attribution_micro_game_7d_roi"] = ratio(sums.get("attribution_micro_game_7d_ltv", ZERO), cost)
    out["cpm_platform"] = ratio(cost * 1000, show, 2)
    out["cpc_platform"] = ratio(cost, click, 2)
    out["active_cost"] = ratio(cost, active, 2)
    out["conversion_cost"] = ratio(cost, convert, 2)
    out["ctr"] = ratio(click * 100, show, 2)
    out["active_rate"] = ratio(active * 100, click, 2)
    out["conversion_rate"] = ratio(convert * 100, click, 2)
    return out


def uni_metrics(sums: dict[str, Decimal]) -> dict[str, Any]:
    """全域合计。ROI 都用合计 GMV / 合计全域成本重算。"""
    total_cost = sums.get("all_stat_total_cost_trend", ZERO)
    out: dict[str, Any] = {name: _money(sums.get(name, ZERO)) for name in UNI_MONEY}
    out["all_roi_trend"] = ratio(sums.get("all_gmv_trend", ZERO), total_cost)
    out["all_roi_24h_trend"] = ratio(sums.get("all_billing_gmv_24h_trend", ZERO), total_cost)
    out["all_roi_0day_trend"] = ratio(sums.get("all_billing_gmv_0day_trend", ZERO), total_cost)
    out["all_roi_3days_trend"] = ratio(sums.get("all_billing_gmv_3days_trend", ZERO), total_cost)
    out["new_project_count"] = int(sums.get("new_project_count", ZERO))
    for name in ZERO_COLUMNS:
        out[name] = 0
    return out


def drama_age(publish_date: date | None, start: date, end: date) -> str:
    """发布日期落在所选区间内是新剧，更早是老剧。没有发布日期按老剧。"""
    if publish_date is not None and start <= publish_date <= end:
        return "新剧"
    return "老剧"


def parse_publish_date(value: str | None) -> date | None:
    text = (value or "").strip()
    if len(text) < 10:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _hour_stamp(value: str | None) -> str | None:
    """快照小时串收成北京时间 +08:00。"""
    if not value:
        return None
    try:
        parsed = datetime.strptime(value[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return value
    return parsed.replace(tzinfo=BEIJING).isoformat()


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    stamp = beijing_stamp(value)
    return stamp.replace(" ", "T") + "+08:00"


def link_passes(link: ProjectLink, query: ManhuaQuery) -> bool:
    """剧、媒体、类型、渠道、投放类型、面板、新/老剧。团队和优化师按行判断。"""
    if link.charge_mode != query.charge_mode:
        return False
    if query.media != MEDIA_OCEAN:
        return False
    if query.series_id and link.series_id not in query.series_id:
        return False
    if query.series_name and query.series_name.strip() not in link.book_name:
        return False
    if query.drama_type and link.drama_type not in query.drama_type:
        return False
    if query.channel and link.channel not in query.channel:
        return False
    if query.bid_type and link.bid_type not in query.bid_type:
        return False
    if query.panel and link.bid_panel not in query.panel:
        return False
    if query.drama_age and drama_age(link.publish_date, query.date_start, query.date_end) not in query.drama_age:
        return False
    return True


def _people_pass(query: ManhuaQuery, teams: set[str], pitchers: set[str]) -> bool:
    if query.team and teams.isdisjoint(query.team):
        return False
    if query.pitcher and pitchers.isdisjoint(query.pitcher):
        return False
    return True


def _joined(values: Iterable[str]) -> str:
    return SEP.join(sorted({value for value in values if value}))


def manhua_drama_rows(
    facts: list[ManhuaFact],
    links: dict[int, ProjectLink],
    query: ManhuaQuery,
    user_id: int | None,
) -> list[dict[str, Any]]:
    """一部剧一行（付费再按面板拆）。投手合并成一格，指标是这些投手之和。

    user_id 为空时不过滤投手，给定时任务把全部行写入日表。
    """
    groups: dict[tuple[int, str], dict[str, Any]] = {}
    for fact in facts:
        link = links.get(fact.project_id)
        if link is None or not link_passes(link, query):
            continue
        panel = link.bid_panel if query.charge_mode == "IAP" else ""
        key = (link.series_id, panel)
        group = groups.get(key)
        if group is None:
            group = {
                "link": link,
                "sums": {},
                "pitcher_ids": set(),
                "pitchers": set(),
                "teams": set(),
                "bid_types": set(),
                "panels": set(),
                "costed": set(),
            }
            groups[key] = group
        _add(group["sums"], fact.metrics, MANHUA_BASE)
        group["pitcher_ids"].add(link.pitcher_id)
        group["pitchers"].add(link.pitcher_name)
        group["teams"].add(link.department_name)
        group["bid_types"].add(link.bid_type)
        group["panels"].add(link.bid_panel)
        if Decimal(fact.metrics.get("stat_cost") or 0) > 0:
            group["costed"].add(fact.promotion_id)
    rows: list[dict[str, Any]] = []
    for (series_id, panel), group in groups.items():
        if user_id is not None and user_id not in group["pitcher_ids"]:
            continue
        if not _people_pass(query, group["teams"], group["pitchers"]):
            continue
        link: ProjectLink = group["link"]
        sums = {name: group["sums"].get(name, ZERO) for name in MANHUA_BASE}
        rows.append(
            {
                "series_id": series_id,
                "book_name": link.book_name,
                "media": MEDIA_OCEAN,
                "drama_type": link.drama_type,
                "channel": link.channel,
                "bid_type": _joined(group["bid_types"]),
                "panel": panel if query.charge_mode == "IAP" else _joined(group["panels"]),
                "drama_age": drama_age(link.publish_date, query.date_start, query.date_end),
                "teams": _joined(group["teams"]),
                "pitchers": _joined(group["pitchers"]),
                "promotion_with_cost_count": len(group["costed"]),
                "pitcher_ids": sorted(group["pitcher_ids"]),
                "pitcher_names": sorted(name for name in group["pitchers"] if name),
                "department_names": sorted(name for name in group["teams"] if name),
                "bid_types": sorted(name for name in group["bid_types"] if name),
                "panel_names": sorted(name for name in group["panels"] if name),
                "panel_key": panel,
                "costed_promotion_ids": sorted(group["costed"]),
                "publish_date": link.publish_date,
                "_sums": sums,
                **manhua_metrics(sums),
            }
        )
    return rows


def _project_head(link: ProjectLink) -> dict[str, Any]:
    return {
        "series_id": link.series_id,
        "book_name": link.book_name,
        "pitcher": link.pitcher_name,
        "team": link.department_name,
        "project_budget": None if link.project_budget is None else _money(link.project_budget),
        "roi_goal": None if link.roi_goal is None else round(float(link.roi_goal), 3),
    }


def _earliest(current: str | None, candidate: str | None) -> str | None:
    if candidate is None:
        return current
    if current is None or candidate < current:
        return candidate
    return current


def manhua_project_rows(
    facts: list[ManhuaFact],
    links: dict[int, ProjectLink],
    query: ManhuaQuery,
    user_id: int | None,
    first_cost: dict[int, str] | None = None,
) -> list[dict[str, Any]]:
    """一个项目一行。user_id 为空时写出全部投手，给定时任务刷日表。"""
    groups: dict[int, dict[str, Any]] = {}
    for fact in facts:
        link = links.get(fact.project_id)
        if link is None or not link_passes(link, query):
            continue
        if user_id is not None and link.pitcher_id != user_id:
            continue
        if not _people_pass(query, {link.department_name}, {link.pitcher_name}):
            continue
        group = groups.setdefault(fact.project_id, {"link": link, "sums": {}, "name": "", "first": None})
        _add(group["sums"], fact.metrics, MANHUA_BASE)
        group["name"] = group["name"] or fact.project_name
        group["first"] = _earliest(group["first"], fact.first_cost_hour)
    rows: list[dict[str, Any]] = []
    for project_id, group in groups.items():
        link = group["link"]
        first = (first_cost or {}).get(project_id, group["first"])
        sums = {name: group["sums"].get(name, ZERO) for name in MANHUA_BASE}
        rows.append(
            {
                "project_id": project_id,
                "project_name": group["name"],
                **_project_head(link),
                "pitcher_id": link.pitcher_id,
                "bid_type": link.bid_type,
                "drama_type": link.drama_type,
                "channel": link.channel,
                "panel": link.bid_panel,
                "publish_date": link.publish_date,
                "created_at": _iso(link.created_at),
                "first_cost_time": _hour_stamp(first),
                "_sums": sums,
                **manhua_metrics(sums),
            }
        )
    return rows


def manhua_promotion_rows(
    facts: list[ManhuaFact],
    links: dict[int, ProjectLink],
    promotions: dict[int, PromotionLink],
    query: ManhuaQuery,
    user_id: int | None,
    first_cost: dict[int, str] | None = None,
) -> list[dict[str, Any]]:
    """一条广告一行。广告须在中台 delivery_task_promotion 里。user_id 为空时写出全部投手。"""
    rows: list[dict[str, Any]] = []
    for fact in facts:
        promotion = promotions.get(fact.promotion_id)
        if promotion is None:
            continue
        link = links.get(promotion.project_id)
        if link is None or not link_passes(link, query):
            continue
        if user_id is not None and link.pitcher_id != user_id:
            continue
        if not _people_pass(query, {link.department_name}, {link.pitcher_name}):
            continue
        first = (first_cost or {}).get(fact.promotion_id, fact.first_cost_hour)
        sums: dict[str, Decimal] = {}
        _add(sums, fact.metrics, MANHUA_BASE)
        rows.append(
            {
                "promotion_id": fact.promotion_id,
                "promotion_name": fact.promotion_name,
                "project_id": promotion.project_id,
                "project_name": fact.project_name,
                **_project_head(link),
                "pitcher_id": link.pitcher_id,
                "bid_type": link.bid_type,
                "drama_type": link.drama_type,
                "channel": link.channel,
                "panel": link.bid_panel,
                "publish_date": link.publish_date,
                "created_at": _iso(promotion.created_at),
                "first_cost_time": _hour_stamp(first),
                "_sums": sums,
                **manhua_metrics(sums),
            }
        )
    return rows


def manhua_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """顶部汇总。ROI = 合计回收 / 合计消耗。"""
    sums: dict[str, Decimal] = {}
    for row in rows:
        for name in MANHUA_BASE:
            sums[name] = sums.get(name, ZERO) + Decimal(str(row.get(name) or 0))
    out = manhua_metrics(sums)
    out["promotion_with_cost_count"] = sum(int(row.get("promotion_with_cost_count") or 0) for row in rows)
    return out


def sort_rows(rows: list[dict[str, Any]], sort_by: str, order: str) -> list[dict[str, Any]]:
    """数值列排序，缺值当 0。同值按原顺序。"""
    return sorted(rows, key=lambda row: row.get(sort_by) or 0, reverse=order == "desc")


def _day_of(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(BEIJING).date().isoformat()


def _in_range(day: str | None, start: date, end: date) -> bool:
    return day is not None and start.isoformat() <= day <= end.isoformat()


def uni_drama_rows(
    facts: list[UniFact],
    links: dict[int, ProjectLink],
    start: date,
    end: date,
    user_id: int | None,
    series_name: str | None = None,
    by_pitcher: bool = False,
) -> list[dict[str, Any]]:
    """全域剧目，日期也是列。

    短剧收益：一部剧一天一行，指标是该剧当天全部投手之和，当前用户须是其中之一。
    投手短剧收益（by_pitcher）：一个投手一部剧一天一行，只算该投手自己的项目，只看自己。
    """
    groups: dict[tuple[int, int, str], dict[str, Any]] = {}

    def group_for(link: ProjectLink, day: str) -> dict[str, Any]:
        key = (link.pitcher_id if by_pitcher else 0, link.series_id, day)
        group = groups.setdefault(key, {"link": link, "sums": {}, "pitcher_ids": set()})
        group["pitcher_ids"].add(link.pitcher_id)
        return group

    for fact in facts:
        link = links.get(fact.project_id)
        if link is None:
            continue
        _add(group_for(link, fact.day)["sums"], fact.metrics, UNI_MONEY)
    for link in links.values():
        day = _day_of(link.created_at)
        if link.stored and _in_range(day, start, end):
            sums = group_for(link, day)["sums"]
            sums["new_project_count"] = sums.get("new_project_count", ZERO) + 1
    rows: list[dict[str, Any]] = []
    for (pitcher_id, series_id, day), group in groups.items():
        link = group["link"]
        if user_id is not None and user_id not in group["pitcher_ids"]:
            continue
        if by_pitcher and user_id is not None and pitcher_id != user_id:
            continue
        if series_name and series_name.strip() not in link.book_name:
            continue
        row: dict[str, Any] = {
            "series_id": series_id,
            "book_name": link.book_name,
            "platform_name": link.channel,
            "stat_time_day": day,
        }
        if by_pitcher:
            row["pitcher_user_id"] = pitcher_id
            row["pitcher_name"] = link.pitcher_name
        sums = {name: group["sums"].get(name, ZERO) for name in (*UNI_MONEY, "new_project_count")}
        row["pitcher_ids"] = sorted(group["pitcher_ids"])
        row["_sums"] = sums
        row.update(uni_metrics(sums))
        rows.append(row)
    return rows


def _days(start: date, end: date) -> list[str]:
    out: list[str] = []
    cursor = start
    while cursor <= end:
        out.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return out


def _bucket_rows(
    facts: list[UniFact],
    links: dict[int, ProjectLink],
    start: date,
    end: date,
    key_of: Any,
) -> dict[tuple[int, str], dict[str, Decimal]]:
    """按（键，天）合计。键由 key_of(link) 给，返回 None 的项目不计。"""
    buckets: dict[tuple[int, str], dict[str, Decimal]] = defaultdict(dict)
    for fact in facts:
        link = links.get(fact.project_id)
        if link is None:
            continue
        key = key_of(link)
        if key is None:
            continue
        _add(buckets[(key, fact.day)], fact.metrics, UNI_MONEY)
    for link in links.values():
        day = _day_of(link.created_at)
        if not link.stored or not _in_range(day, start, end):
            continue
        key = key_of(link)
        if key is None:
            continue
        sums = buckets[(key, day)]
        sums["new_project_count"] = sums.get("new_project_count", ZERO) + 1
    return buckets


def uni_pitcher_rows(
    facts: list[UniFact],
    links: dict[int, ProjectLink],
    start: date,
    end: date,
    user_id: int | None,
) -> list[dict[str, Any]]:
    """投手报表：一个投手一天一行。user_id 为空时写出全部投手。"""
    names = {link.pitcher_id: link.pitcher_name for link in links.values()}
    buckets = _bucket_rows(
        facts,
        links,
        start,
        end,
        lambda link: link.pitcher_id if user_id is None or link.pitcher_id == user_id else None,
    )
    return [
        {
            "pitcher_user_id": pitcher_id,
            "pitcher_name": names.get(pitcher_id, ""),
            "stat_time_day": day,
            "_sums": {name: sums.get(name, ZERO) for name in (*UNI_MONEY, "new_project_count")},
            **uni_metrics(sums),
            "new_drama_count": 0,
        }
        for (pitcher_id, day), sums in sorted(buckets.items(), key=lambda item: item[0][1], reverse=True)
    ]


def uni_group_rows(
    facts: list[UniFact],
    links: dict[int, ProjectLink],
    start: date,
    end: date,
    department_ids: set[int] | None,
) -> list[dict[str, Any]]:
    """组报表：一个部门一天一行。department_ids 为空时写出全部部门。"""
    names = {link.department_id: link.department_name for link in links.values() if link.department_id is not None}

    def key_of(link: ProjectLink) -> int | None:
        if link.department_id is None:
            return None
        if department_ids is not None and link.department_id not in department_ids:
            return None
        return link.department_id

    buckets = _bucket_rows(facts, links, start, end, key_of)
    return [
        {
            "department_id": department_id,
            "department_name": names.get(department_id, ""),
            "stat_time_day": day,
            "_sums": {name: sums.get(name, ZERO) for name in (*UNI_MONEY, "new_project_count")},
            **uni_metrics(sums),
            "new_drama_count": 0,
        }
        for (department_id, day), sums in sorted(buckets.items(), key=lambda item: item[0][1], reverse=True)
    ]


def uni_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """顶部汇总。ROI = 合计 GMV / 合计全域成本。"""
    sums: dict[str, Decimal] = {}
    for row in rows:
        for name in (*UNI_MONEY, "new_project_count"):
            sums[name] = sums.get(name, ZERO) + Decimal(str(row.get(name) or 0))
    return uni_metrics(sums)


def arrived_hours(day: date, now: datetime) -> list[int]:
    """所选日已经到了的小时（北京时间）。将来的日子为空，过去的日子 0–23。"""
    today = now.astimezone(BEIJING).date()
    if day > today:
        return []
    if day < today:
        return list(range(24))
    return list(range(now.astimezone(BEIJING).hour + 1))


def manhua_trend(day: date, hourly: dict[int, tuple[Decimal, Decimal]], now: datetime) -> dict[str, Any]:
    """一天按小时的消耗和回收。没到的小时不返回，到了没数据补 0。"""
    items = []
    for hour in arrived_hours(day, now):
        cost, pay = hourly.get(hour, (ZERO, ZERO))
        items.append({"hour": hour, "stat_cost": _money(cost), "stat_pay_amount": _money(pay)})
    return {"date": day.isoformat(), "items": items}


def uni_speed(
    day: date,
    current: dict[int, Decimal],
    previous: dict[int, Decimal],
    now: datetime,
) -> dict[str, Any]:
    """所选日与前一天按小时对比。回收没有数据源，结构保留、数组为空。"""
    hours = arrived_hours(day, now)
    previous_day = day - timedelta(days=1)
    previous_hours = arrived_hours(previous_day, now)
    cost = {
        "current": [{"hour": hour, "value": _money(current.get(hour, ZERO))} for hour in hours],
        "previous": [{"hour": hour, "value": _money(previous.get(hour, ZERO))} for hour in previous_hours],
        "growth_rate": [
            {
                "hour": hour,
                "rate": ratio(current.get(hour, ZERO) - previous.get(hour, ZERO), previous.get(hour, ZERO)),
            }
            for hour in hours
        ],
    }
    return {
        "date": day.isoformat(),
        "previous_date": previous_day.isoformat(),
        "cost": cost,
        "recovery": {"current": [], "previous": [], "growth_rate": []},
    }
