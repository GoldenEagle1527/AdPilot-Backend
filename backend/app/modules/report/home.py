"""首页五张卡和一条曲线。只读已有快照和日表，不调巨量，GET 不写缺省字段。"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.times import BEIJING
from app.modules.account.model import OeDeliveryReport, OeUniProjectReport
from app.modules.report import crud
from app.modules.report.fold import fold_manhua_dramas
from app.modules.report.pages import visible_departments
from app.modules.report.schema import ManhuaMetrics, ManhuaQuery, UniMetrics
from app.modules.report.service import (
    MANHUA_BASE,
    UNI_MONEY,
    ZERO,
    ManhuaFact,
    ProjectLink,
    manhua_drama_rows,
    manhua_metrics,
    ratio,
    uni_metrics,
)
from app.modules.report.serving import (
    ReportHomeField,
    ReportManhuaDramaDay,
    ReportManhuaPromotionDay,
    ReportUniDramaDay,
    ReportUniGroupDay,
    ReportUniPitcherDay,
    ReportUniPitcherDramaDay,
)
from app.modules.system_admin.domain.models import User
from app.modules.system_admin.domain.scope import resolve_data_scope

SURFACES = ("manhua", "uni_drama", "uni_pitcher_drama", "uni_pitcher", "uni_group")
MANHUA_DEFAULT = ("stat_cost", "click_cnt", "convert_cnt")
UNI_DEFAULT = ("all_stat_cost_trend", "all_gmv_trend", "all_roi_trend")
CTR = "ctr"
UNI_COUNTS = ("all_show_cnt_trend", "all_click_cnt_trend")
UNI_RAW = (*UNI_MONEY, *UNI_COUNTS, "new_project_count")

_MANHUA_OPTIONAL = tuple(ManhuaMetrics.model_fields) + ("promotion_with_cost_count",)
_UNI_OPTIONAL = tuple(UniMetrics.model_fields)
_UNI_OWN_OPTIONAL = _UNI_OPTIONAL + ("new_drama_count",)
_OPTIONAL = {
    "manhua": _MANHUA_OPTIONAL,
    "uni_drama": _UNI_OPTIONAL,
    "uni_pitcher_drama": _UNI_OPTIONAL,
    "uni_pitcher": _UNI_OWN_OPTIONAL,
    "uni_group": _UNI_OWN_OPTIONAL,
}
_DRAMA_OWN = ("uni_drama", "uni_pitcher_drama")
_PITCHER_DAY = {
    "uni_drama": ReportUniPitcherDramaDay,
    "uni_pitcher_drama": ReportUniPitcherDramaDay,
    "uni_pitcher": ReportUniPitcherDay,
    "uni_group": ReportUniPitcherDay,
}


@dataclass(frozen=True)
class HomeQuery:
    surface: str
    charge_mode: str | None = None
    date_start: date | None = None
    date_end: date | None = None
    user_ids: tuple[int, ...] = ()
    department_ids: tuple[int, ...] = ()
    curve: str | None = None


def optional_fields(surface: str) -> tuple[str, ...]:
    return _OPTIONAL[surface]


def _check_query(query: HomeQuery) -> None:
    if query.surface not in SURFACES:
        raise ApiError(422, "首页表面不正确")
    if query.surface == "manhua":
        if query.charge_mode not in ("IAA", "IAP"):
            raise ApiError(422, "漫剧首页必须带收费模式")
    elif query.charge_mode is not None:
        raise ApiError(422, "该表面不能带收费模式")
    if (query.date_start is None) ^ (query.date_end is None):
        raise ApiError(422, "日期须成对传入")
    if query.date_start is not None and query.date_end is not None and query.date_start > query.date_end:
        raise ApiError(422, "日期段起不能晚于止")


def _check_fields(surface: str, fields: list[str]) -> None:
    allowed = set(optional_fields(surface))
    if len(fields) != 3 or len(set(fields)) != 3 or any(name not in allowed for name in fields):
        raise ApiError(422, "自选字段须恰好三个、互不相同，且都在该表面可选集里")


def _kind(surface: str) -> str:
    return "manhua" if surface == "manhua" else "uni"


def _show_key(surface: str) -> str:
    return "show_cnt" if surface == "manhua" else "all_show_cnt_trend"


def _click_key(surface: str) -> str:
    return "click_cnt" if surface == "manhua" else "all_click_cnt_trend"


def _defaults(surface: str) -> tuple[str, str, str]:
    return MANHUA_DEFAULT if surface == "manhua" else UNI_DEFAULT


def _dec(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def _add(target: dict[str, Decimal], source: dict[str, Any], names: Iterable[str]) -> None:
    for name in names:
        target[name] = target.get(name, ZERO) + _dec(source.get(name))


def card_value(surface: str, sums: dict[str, Decimal], key: str, promotion_count: int = 0) -> int | float:
    """用这一桶的分子分母算一个键。点击率是点击 / 展示 × 100，展示为 0 则为 0。"""
    if key == CTR:
        return ratio(sums.get(_click_key(surface), ZERO) * 100, sums.get(_show_key(surface), ZERO), 2)
    if key == _show_key(surface):
        return int(sums.get(key, ZERO))
    if key == "promotion_with_cost_count":
        return int(promotion_count)
    if key == "new_drama_count":
        return 0
    metrics = manhua_metrics(sums) if surface == "manhua" else uni_metrics(sums)
    return metrics[key]


def _cards(surface: str, sums: dict[str, Decimal], fields: tuple[str, str, str], promotion_count: int) -> list[dict[str, Any]]:
    keys = (_show_key(surface), CTR, *fields)
    return [{"key": key, "value": card_value(surface, sums, key, promotion_count)} for key in keys]


def _point(surface: str, sums: dict[str, Decimal], key: str, promotion_count: int, **stamp: Any) -> dict[str, Any]:
    return {**stamp, "value": card_value(surface, sums, key, promotion_count)}


def _view(
    query: HomeQuery,
    fields: tuple[str, str, str],
    curve_key: str,
    grain: str,
    sums: dict[str, Decimal],
    promotion_count: int,
    points: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "surface": query.surface,
        "charge_mode": query.charge_mode if query.surface == "manhua" else None,
        "grain": grain,
        "cards": _cards(query.surface, sums, fields, promotion_count),
        "curve": {"key": curve_key, "grain": grain, "points": points},
    }


def _empty(query: HomeQuery, fields: tuple[str, str, str], curve_key: str, grain: str) -> dict[str, Any]:
    return _view(query, fields, curve_key, grain, {}, 0, [])


def _grain(query: HomeQuery) -> str:
    if query.date_start is not None and query.date_end is not None and query.date_start == query.date_end:
        return "hour"
    return "day"


def _curve_key(query: HomeQuery, fields: tuple[str, str, str]) -> str:
    chosen = query.curve or _show_key(query.surface)
    if chosen not in {_show_key(query.surface), CTR, *fields}:
        raise ApiError(422, "曲线字段不在当前五张卡里")
    return chosen


async def _saved_fields(session: AsyncSession, user_id: int, surface: str) -> tuple[str, str, str] | None:
    row = await session.scalar(
        select(ReportHomeField).where(
            ReportHomeField.user_id == user_id,
            ReportHomeField.surface == surface,
            ReportHomeField.is_deleted == 0,
        )
    )
    if row is None:
        return None
    return (row.field_1, row.field_2, row.field_3)


async def _pitchers(session: AsyncSession, query: HomeQuery) -> set[int] | None:
    """空筛选返回 None。有值时是点名用户，并上这些部门自己的未删除用户。"""
    if not query.user_ids and not query.department_ids:
        return None
    found = {int(item) for item in query.user_ids}
    if query.department_ids:
        rows = await session.scalars(
            select(User.id).where(
                User.department_id.in_(list({int(item) for item in query.department_ids})),
                User.is_deleted == 0,
            )
        )
        found.update(int(item) for item in rows.all())
    return found


async def _keep_group_pitchers(
    session: AsyncSession, candidates: set[int], visible: set[int] | None
) -> set[int]:
    """只留当前部门仍在可见部门里的人。负责人的可见部门是全部。"""
    if not candidates:
        return set()
    rows = await session.execute(
        select(User.id, User.department_id).where(
            User.id.in_(list(candidates)),
            User.is_deleted == 0,
        )
    )
    kept: set[int] = set()
    for user_id, department_id in rows.all():
        if department_id is None:
            continue
        if visible is not None and int(department_id) not in visible:
            continue
        kept.add(int(user_id))
    return kept


def _date_filters(model: Any, query: HomeQuery) -> list[Any]:
    filters = [model.is_deleted == 0]
    if query.date_start is not None and query.date_end is not None:
        filters.append(model.stat_date >= query.date_start)
        filters.append(model.stat_date <= query.date_end)
    return filters


def _pack_manhua_drama(row: ReportManhuaDramaDay) -> dict[str, Any]:
    return {
        "stat_date": row.stat_date,
        "series_id": row.series_id,
        "panel_key": row.panel_key,
        "book_name": row.book_name,
        "drama_type": row.drama_type,
        "channel": row.channel,
        "publish_date": row.publish_date,
        "pitcher_ids": list(row.pitcher_ids or []),
        "pitcher_names": list(row.pitcher_names or []),
        "department_names": list(row.department_names or []),
        "bid_types": list(row.bid_types or []),
        "panel_names": list(row.panel_names or []),
        "costed_promotion_ids": list(row.costed_promotion_ids or []),
        **{name: getattr(row, name) for name in MANHUA_BASE},
    }


def _pack_manhua_promotion(row: ReportManhuaPromotionDay) -> dict[str, Any]:
    return {
        "stat_date": row.stat_date,
        "promotion_id": int(row.promotion_id),
        "pitcher_id": int(row.pitcher_id),
        **{name: getattr(row, name) for name in MANHUA_BASE},
    }


def _pack_uni(row: Any, *, pitcher: bool) -> dict[str, Any]:
    packed = {
        "stat_date": row.stat_date,
        "pitcher_ids": list(getattr(row, "pitcher_ids", []) or []),
        "pitcher_id": getattr(row, "pitcher_id", None),
        "department_id": getattr(row, "department_id", None),
    }
    for name in UNI_RAW:
        packed[name] = getattr(row, name, 0)
    if pitcher:
        packed["pitcher_id"] = int(row.pitcher_id)
    return packed


def _manhua_query(charge_mode: str, start: date | None, end: date | None) -> ManhuaQuery:
    return ManhuaQuery(
        charge_mode=charge_mode,  # type: ignore[arg-type]
        date_start=start or date(2000, 1, 1),
        date_end=end or date(2099, 12, 31),
    )


def _folded_bucket(rows: list[dict[str, Any]], charge_mode: str, viewer: int | None, start: date | None, end: date | None) -> tuple[dict[str, Decimal], int]:
    folded = fold_manhua_dramas(rows, _manhua_query(charge_mode, start, end), viewer)
    sums: dict[str, Decimal] = {}
    for row in folded:
        _add(sums, row, MANHUA_BASE)
    count = sum(int(row.get("promotion_with_cost_count") or 0) for row in folded)
    return sums, count


def _promotion_bucket(rows: list[dict[str, Any]]) -> tuple[dict[str, Decimal], int]:
    sums: dict[str, Decimal] = {}
    costed: set[int] = set()
    for row in rows:
        _add(sums, row, MANHUA_BASE)
        if _dec(row.get("stat_cost")) > 0:
            costed.add(int(row["promotion_id"]))
    return sums, len(costed)


def _uni_bucket(rows: list[dict[str, Any]]) -> dict[str, Decimal]:
    sums: dict[str, Decimal] = {}
    for row in rows:
        _add(sums, row, UNI_RAW)
    return sums


def _by_date(rows: list[dict[str, Any]]) -> dict[date, list[dict[str, Any]]]:
    grouped: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["stat_date"]].append(row)
    return grouped


def _day_points_manhua(
    surface: str,
    grouped: dict[date, list[dict[str, Any]]],
    curve_key: str,
    *,
    charge_mode: str,
    viewer: int | None,
    filtered: bool,
) -> list[dict[str, Any]]:
    points = []
    for day in sorted(grouped):
        chunk = grouped[day]
        if not chunk:
            continue
        if filtered:
            sums, count = _promotion_bucket(chunk)
        else:
            folded = fold_manhua_dramas(chunk, _manhua_query(charge_mode, day, day), viewer)
            if not folded:
                continue
            sums, count = _folded_bucket(chunk, charge_mode, viewer, day, day)
        points.append(_point(surface, sums, curve_key, count, date=day.isoformat()))
    return points


def _day_points_uni(surface: str, grouped: dict[date, list[dict[str, Any]]], curve_key: str) -> list[dict[str, Any]]:
    return [
        _point(surface, _uni_bucket(grouped[day]), curve_key, 0, date=day.isoformat())
        for day in sorted(grouped)
        if grouped[day]
    ]


def _hour_of_created(value: datetime | None, day: date) -> int | None:
    if value is None:
        return None
    local = value.astimezone(BEIJING)
    if local.date() != day:
        return None
    return local.hour


def _manhua_facts(hour_rows: list[tuple[int, int, int, dict[str, Decimal]]], hour: int | None) -> list[ManhuaFact]:
    grouped: dict[tuple[int, int], dict[str, Decimal]] = {}
    for stamp, project_id, promotion_id, metrics in hour_rows:
        if hour is not None and stamp != hour:
            continue
        bucket = grouped.setdefault((project_id, promotion_id), {})
        _add(bucket, metrics, MANHUA_BASE)
    return [
        ManhuaFact(project_id=project_id, promotion_id=promotion_id, metrics=metrics)
        for (project_id, promotion_id), metrics in grouped.items()
    ]


def _drama_key(link: ProjectLink, charge_mode: str) -> tuple[int, str]:
    panel = link.bid_panel if charge_mode == "IAP" else ""
    return (link.series_id, panel)


def _rows_bucket(rows: list[dict[str, Any]]) -> tuple[dict[str, Decimal], int]:
    sums: dict[str, Decimal] = {}
    for row in rows:
        _add(sums, row.get("_sums") or {}, MANHUA_BASE)
    count = sum(int(row.get("promotion_with_cost_count") or 0) for row in rows)
    return sums, count


def _visible_manhua_rows(
    facts: list[ManhuaFact], links: dict[int, ProjectLink], charge_mode: str, day: date, viewer: int | None
) -> list[dict[str, Any]]:
    return manhua_drama_rows(facts, links, _manhua_query(charge_mode, day, day), viewer)


def _filtered_hour_manhua(
    hour_rows: list[tuple[int, int, int, dict[str, Decimal]]],
    links: dict[int, ProjectLink],
    allowed: set[int],
) -> tuple[dict[str, Decimal], int, dict[int, tuple[dict[str, Decimal], int]]]:
    total: dict[str, Decimal] = {}
    costed: set[int] = set()
    per_hour: dict[int, tuple[dict[str, Decimal], set[int]]] = {}
    for hour, project_id, promotion_id, metrics in hour_rows:
        link = links.get(project_id)
        if link is None or link.pitcher_id not in allowed:
            continue
        _add(total, metrics, MANHUA_BASE)
        sums, seen = per_hour.setdefault(hour, ({}, set()))
        _add(sums, metrics, MANHUA_BASE)
        if _dec(metrics.get("stat_cost")) > 0:
            costed.add(promotion_id)
            seen.add(promotion_id)
    hours = {hour: (sums, len(seen)) for hour, (sums, seen) in per_hour.items()}
    return total, len(costed), hours


def _uni_keep(
    surface: str,
    link: ProjectLink,
    *,
    viewer: int | None,
    allowed: set[int] | None,
    visible_series: set[int] | None,
    visible_departments_ids: set[int] | None,
) -> bool:
    if allowed is not None:
        return link.pitcher_id in allowed
    if surface == "uni_drama":
        return viewer is None or link.series_id in (visible_series or set())
    if surface == "uni_group":
        if link.department_id is None:
            return False
        return visible_departments_ids is None or link.department_id in visible_departments_ids
    return viewer is None or link.pitcher_id == viewer


def _visible_series(links: dict[int, ProjectLink], viewer: int | None) -> set[int]:
    if viewer is None:
        return {link.series_id for link in links.values()}
    return {link.series_id for link in links.values() if link.pitcher_id == viewer}


def _uni_hour_buckets(
    surface: str,
    hour_rows: list[tuple[int, int, dict[str, Decimal]]],
    links: dict[int, ProjectLink],
    day: date,
    *,
    viewer: int | None,
    allowed: set[int] | None,
    visible_departments_ids: set[int] | None,
) -> tuple[dict[str, Decimal], dict[int, dict[str, Decimal]]]:
    series = _visible_series(links, viewer) if surface == "uni_drama" and allowed is None else None
    total: dict[str, Decimal] = {}
    per_hour: dict[int, dict[str, Decimal]] = {}
    seen_hours: set[int] = set()
    for hour, project_id, metrics in hour_rows:
        link = links.get(project_id)
        if link is None or not _uni_keep(
            surface,
            link,
            viewer=viewer,
            allowed=allowed,
            visible_series=series,
            visible_departments_ids=visible_departments_ids,
        ):
            continue
        _add(total, metrics, (*UNI_MONEY, *UNI_COUNTS))
        _add(per_hour.setdefault(hour, {}), metrics, (*UNI_MONEY, *UNI_COUNTS))
        seen_hours.add(hour)
    for link in links.values():
        if not link.stored or not _uni_keep(
            surface,
            link,
            viewer=viewer,
            allowed=allowed,
            visible_series=series,
            visible_departments_ids=visible_departments_ids,
        ):
            continue
        created = _hour_of_created(link.created_at, day)
        if created is None:
            continue
        total["new_project_count"] = total.get("new_project_count", ZERO) + 1
        if created in seen_hours:
            bucket = per_hour.setdefault(created, {})
            bucket["new_project_count"] = bucket.get("new_project_count", ZERO) + 1
    return total, per_hour


async def _manhua_hour_rows(
    session: AsyncSession, day: date, charge_mode: str
) -> list[tuple[int, int, int, dict[str, Decimal]]]:
    low = f"{day.isoformat()} 00:00:00"
    high = f"{day.isoformat()} 23:59:59"
    report = OeDeliveryReport
    rows = await session.execute(
        select(
            report.stat_time_hour,
            report.cdp_project_id,
            report.cdp_promotion_id,
            *[func.sum(getattr(report, name)) for name in MANHUA_BASE],
        )
        .where(
            report.is_deleted == 0,
            report.stat_time_hour >= low,
            report.stat_time_hour <= high,
            report.cdp_project_id.in_(crud._standard_project_ids(charge_mode)),
        )
        .group_by(report.stat_time_hour, report.cdp_project_id, report.cdp_promotion_id)
    )
    out = []
    for stamp, project_id, promotion_id, *sums in rows.all():
        hour = crud._hour_of(stamp)
        if hour is None:
            continue
        out.append(
            (
                hour,
                int(project_id),
                int(promotion_id),
                {name: _dec(value) for name, value in zip(MANHUA_BASE, sums)},
            )
        )
    return out


async def _uni_hour_rows(session: AsyncSession, day: date) -> list[tuple[int, int, dict[str, Decimal]]]:
    low = f"{day.isoformat()} 00:00:00"
    high = f"{day.isoformat()} 23:59:59"
    report = OeUniProjectReport
    names = (*UNI_MONEY, *UNI_COUNTS)
    rows = await session.execute(
        select(
            report.stat_time_hour,
            report.cdp_project_id,
            *[func.sum(getattr(report, name)) for name in names],
        )
        .where(
            report.is_deleted == 0,
            report.stat_time_hour >= low,
            report.stat_time_hour <= high,
            report.cdp_project_id.in_(crud._uni_project_ids()),
        )
        .group_by(report.stat_time_hour, report.cdp_project_id)
    )
    out = []
    for stamp, project_id, *sums in rows.all():
        hour = crud._hour_of(stamp)
        if hour is None:
            continue
        out.append((hour, int(project_id), {name: _dec(value) for name, value in zip(names, sums)}))
    return out


async def _load_model_rows(session: AsyncSession, model: Any, filters: list[Any]) -> list[Any]:
    rows = await session.scalars(select(model).where(*filters))
    return list(rows.all())


def _filter_uni_days(
    surface: str,
    rows: list[dict[str, Any]],
    *,
    viewer: int | None,
    allowed: set[int] | None,
    departments: set[int] | None,
) -> list[dict[str, Any]]:
    if allowed is not None:
        return [row for row in rows if int(row.get("pitcher_id") or 0) in allowed]
    if surface == "uni_group":
        if departments is None:
            return rows
        return [row for row in rows if row.get("department_id") in departments]
    if surface == "uni_drama":
        if viewer is None:
            return rows
        return [row for row in rows if viewer in list(row.get("pitcher_ids") or [])]
    if viewer is None:
        return rows
    return [row for row in rows if int(row.get("pitcher_id") or 0) == viewer]


async def home_view(session: AsyncSession, principal: dict[str, Any], query: HomeQuery) -> dict[str, Any]:
    """五张卡和本次查询的曲线。单日读小时快照，跨天或不选时间读日表。"""
    _check_query(query)
    from app.modules.report.controller import _user_id, _viewer_id

    user_id = _user_id(principal)
    saved = await _saved_fields(session, user_id, query.surface)
    fields = saved or _defaults(query.surface)
    curve_key = _curve_key(query, fields)
    grain = _grain(query)
    viewer = await _viewer_id(session, principal)
    pitchers = await _pitchers(session, query)
    departments: set[int] | None = None
    if query.surface == "uni_group":
        scope = await resolve_data_scope(session, principal)
        departments = await visible_departments(session, scope, see_all=viewer is None)
    if pitchers is not None:
        if query.surface == "uni_group":
            pitchers = await _keep_group_pitchers(session, pitchers, departments)
        elif viewer is not None:
            pitchers = pitchers & {viewer}
        if not pitchers:
            return _empty(query, fields, curve_key, grain)

    if grain == "hour":
        assert query.date_start is not None
        return await _hour_view(
            session,
            query,
            fields,
            curve_key,
            viewer,
            pitchers,
            departments,
        )
    return await _day_view(session, query, fields, curve_key, grain, viewer, pitchers, departments)


async def _hour_view(
    session: AsyncSession,
    query: HomeQuery,
    fields: tuple[str, str, str],
    curve_key: str,
    viewer: int | None,
    pitchers: set[int] | None,
    departments: set[int] | None,
) -> dict[str, Any]:
    day = query.date_start
    assert day is not None
    if query.surface == "manhua":
        assert query.charge_mode is not None
        hour_rows = await _manhua_hour_rows(session, day, query.charge_mode)
        project_ids = {project_id for _, project_id, _, _ in hour_rows}
        links = await crud.standard_links(session, charge_mode=query.charge_mode, project_ids=project_ids)
        if pitchers is None:
            visible = _visible_manhua_rows(_manhua_facts(hour_rows, None), links, query.charge_mode, day, viewer)
            visible_keys = {(int(row["series_id"]), str(row.get("panel_key") or "")) for row in visible}
            sums, count = _rows_bucket(visible)
            points = []
            for hour in sorted({item[0] for item in hour_rows}):
                kept = [
                    fact
                    for fact in _manhua_facts(hour_rows, hour)
                    if (link := links.get(fact.project_id)) is not None
                    and _drama_key(link, query.charge_mode) in visible_keys
                ]
                if not kept:
                    continue
                hour_sums, hour_count = _rows_bucket(
                    manhua_drama_rows(kept, links, _manhua_query(query.charge_mode, day, day), None)
                )
                points.append(_point(query.surface, hour_sums, curve_key, hour_count, hour=hour))
            return _view(query, fields, curve_key, "hour", sums, count, points)
        sums, count, per_hour = _filtered_hour_manhua(hour_rows, links, pitchers)
        points = [
            _point(query.surface, hour_sums, curve_key, hour_count, hour=hour)
            for hour, (hour_sums, hour_count) in sorted(per_hour.items())
        ]
        return _view(query, fields, curve_key, "hour", sums, count, points)

    hour_rows = await _uni_hour_rows(session, day)
    project_ids = {project_id for _, project_id, _ in hour_rows}
    links = await crud.uni_links(session, project_ids=project_ids, created_between=(day, day))
    sums, per_hour = _uni_hour_buckets(
        query.surface,
        hour_rows,
        links,
        day,
        viewer=viewer,
        allowed=pitchers,
        visible_departments_ids=departments if query.surface == "uni_group" and pitchers is None else None,
    )
    points = [
        _point(query.surface, hour_sums, curve_key, 0, hour=hour) for hour, hour_sums in sorted(per_hour.items())
    ]
    return _view(query, fields, curve_key, "hour", sums, 0, points)


async def _day_view(
    session: AsyncSession,
    query: HomeQuery,
    fields: tuple[str, str, str],
    curve_key: str,
    grain: str,
    viewer: int | None,
    pitchers: set[int] | None,
    departments: set[int] | None,
) -> dict[str, Any]:
    if query.surface == "manhua":
        assert query.charge_mode is not None
        if pitchers is None:
            filters = _date_filters(ReportManhuaDramaDay, query)
            filters.append(ReportManhuaDramaDay.charge_mode == query.charge_mode)
            raw = await _load_model_rows(session, ReportManhuaDramaDay, filters)
            rows = [_pack_manhua_drama(row) for row in raw]
            sums, count = _folded_bucket(rows, query.charge_mode, viewer, query.date_start, query.date_end)
            points = _day_points_manhua(
                query.surface,
                _by_date(rows),
                curve_key,
                charge_mode=query.charge_mode,
                viewer=viewer,
                filtered=False,
            )
        else:
            filters = _date_filters(ReportManhuaPromotionDay, query)
            filters.append(ReportManhuaPromotionDay.charge_mode == query.charge_mode)
            filters.append(ReportManhuaPromotionDay.pitcher_id.in_(list(pitchers)))
            raw = await _load_model_rows(session, ReportManhuaPromotionDay, filters)
            rows = [_pack_manhua_promotion(row) for row in raw]
            sums, count = _promotion_bucket(rows)
            points = _day_points_manhua(
                query.surface, _by_date(rows), curve_key, charge_mode=query.charge_mode, viewer=viewer, filtered=True
            )
        return _view(query, fields, curve_key, grain, sums, count, points)

    if pitchers is None and query.surface == "uni_group":
        model = ReportUniGroupDay
    elif pitchers is None and query.surface == "uni_drama":
        model = ReportUniDramaDay
    elif pitchers is None and query.surface == "uni_pitcher_drama":
        model = ReportUniPitcherDramaDay
    elif pitchers is None:
        model = ReportUniPitcherDay
    else:
        model = _PITCHER_DAY[query.surface]
    filters = _date_filters(model, query)
    if pitchers is not None:
        filters.append(model.pitcher_id.in_(list(pitchers)))
    raw = await _load_model_rows(session, model, filters)
    rows = _filter_uni_days(
        query.surface,
        [_pack_uni(row, pitcher=model is not ReportUniDramaDay and model is not ReportUniGroupDay) for row in raw],
        viewer=viewer,
        allowed=None if pitchers is None else pitchers,
        departments=departments if query.surface == "uni_group" and pitchers is None else None,
    )
    sums = _uni_bucket(rows)
    points = _day_points_uni(query.surface, _by_date(rows), curve_key)
    return _view(query, fields, curve_key, grain, sums, 0, points)


async def save_home_fields(
    session: AsyncSession, user_id: int, surface: str, fields: list[str]
) -> dict[str, Any]:
    """整行替换这一账号、这一表面的三个自选。漫剧 IAA/IAP 共用 manhua。"""
    if surface not in SURFACES:
        raise ApiError(422, "首页表面不正确")
    _check_fields(surface, fields)
    row = await session.scalar(
        select(ReportHomeField).where(
            ReportHomeField.user_id == user_id,
            ReportHomeField.surface == surface,
        )
    )
    if row is None:
        row = ReportHomeField(user_id=user_id, surface=surface, field_1=fields[0], field_2=fields[1], field_3=fields[2])
        session.add(row)
    else:
        row.is_deleted = 0
        row.deleted_at = None
        row.field_1 = fields[0]
        row.field_2 = fields[1]
        row.field_3 = fields[2]
    await session.commit()
    return {"surface": surface, "fields": [fields[0], fields[1], fields[2]]}
