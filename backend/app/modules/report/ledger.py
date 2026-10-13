"""利润和素材报表的纯计算。不读库。

回收是素材小时表的 stat_pay_amount。盈亏 = 回收 × 0.95 − 消耗 × 当天 ROI 系数。
系数按统计日取 ROI 配置，重叠取创建时间最新的一条，没配到按 1.00。
跨天合计先把每天的盈亏加起来，回收率用合计回收 / 合计消耗。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable

from app.core.pagination import PageParams, page_slice
from app.core.times import BEIJING
from app.modules.report.service import ratio

ZERO = Decimal("0")
LIBRARY_ID_MAX = 2_147_483_647
SHARE = Decimal("0.95")
DEFAULT_ROI = Decimal("1.00")
SEP = "、"

MATERIAL_TYPE_NAMES = {
    "vertical_video": "竖版视频",
    "horizontal_video": "横版视频",
    "horizontal_image": "大图横图",
    "small_image": "小图",
    "vertical_image": "大图竖图",
}
OWNERSHIP_NAMES = {"public": "公有", "private": "私有"}
PLATFORM_NAMES = {"tomato": "番茄", "ouxi": "鸥溪"}


def library_ids(values: Iterable[int]) -> list[int]:
    """素材库主键是 32 位整数。头条素材 id 是 19 位，不能拿去对主键。"""
    return [int(item) for item in values if 0 < int(item) <= LIBRARY_ID_MAX]


def money(value: Decimal | int) -> float:
    return round(float(value), 2)


def beijing_day(value: datetime | None) -> date | None:
    """带时区的时间换成北京日期。没有时区就取它自己的日期。"""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.date()
    return value.astimezone(BEIJING).date()


def platform_code(channel: str) -> str:
    """渠道名里有鸥溪算鸥溪，其余算番茄。"""
    if "鸥溪" in channel:
        return "ouxi"
    return "tomato"


def is_nobid(scope: str, template_name: str) -> bool:
    """只有标准投放、且模板名含 NB 或 CBO（不区分大小写）才是 nobid。"""
    if scope != "standard":
        return False
    name = template_name.upper()
    return "NB" in name or "CBO" in name


def template_is_nb(template_name: str) -> bool:
    """未上 NB 页：模板名含 NB 或 CBO 就算 NB 计划，标准和全域都算。"""
    name = template_name.upper()
    return "NB" in name or "CBO" in name


def drama_band(estimate: date | None, start: date, end: date) -> str | None:
    """预估可投日落在查询区间内是新剧，区间开始之前是老剧。没有日期或晚于区间则两边都不是。"""
    if estimate is None:
        return None
    if start <= estimate <= end:
        return "新剧"
    if estimate < start:
        return "老剧"
    return None


@dataclass(frozen=True)
class RoiSpan:
    config_id: int
    start: date
    end: date
    rate: Decimal
    created_at: datetime


def roi_for(day: date, spans: Iterable[RoiSpan]) -> Decimal:
    """这一天用哪条系数。重叠取创建时间最新，同一时间再取 id 较大的。"""
    hits = [span for span in spans if span.start <= day <= span.end]
    if not hits:
        return DEFAULT_ROI
    return max(hits, key=lambda span: (span.created_at, span.config_id)).rate


def profit_amount(recovery: Decimal, cost: Decimal, roi: Decimal) -> Decimal:
    return recovery * SHARE - cost * roi


def locked_pitcher(*, owner: bool, admin: bool, user_id: int, requested: int | None) -> int | None:
    """每日利润：负责人和运营管理员可按投手筛，其余账号锁成自己。"""
    if owner or admin:
        return requested
    return user_id


def editor_only(*, owner: bool, admin: bool, role_names: Iterable[str], tag_names: Iterable[str]) -> bool:
    """素材手或剪辑师角色只看自己。负责人和运营管理员看全部。"""
    if owner or admin:
        return False
    names = set(role_names)
    tags = set(tag_names)
    return "剪辑师" in names or "素材手" in tags


def narrow_departments(allowed: set[int] | None, requested: int | None) -> set[int] | None:
    """None 表示不限部门。请求的部门不在可见范围里时返回空集。"""
    if requested is None:
        return allowed
    if allowed is None:
        return {requested}
    if requested not in allowed:
        return set()
    return {requested}


@dataclass(frozen=True)
class RawMaterial:
    stat_date: date
    material_id: int
    material_name: str
    promotion_id: int
    promotion_name: str
    project_id: int
    project_name: str
    stat_cost: Decimal
    recovery: Decimal
    show_cnt: int = 0
    click_cnt: int = 0
    convert_cnt: int = 0


@dataclass(frozen=True)
class VideoCard:
    video_id: int
    name: str
    series_id: int
    book_name: str
    estimate_publish_date: date | None
    material_type: str
    ownership: str
    file_url: str
    uploader_id: int
    uploader_name: str
    uploader_department_id: int | None
    uploader_department_name: str
    pitcher_ids: tuple[int, ...] = ()
    pitcher_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProjectCard:
    project_id: int
    task_id: int
    scope: str
    template_name: str
    charge_mode: str
    series_id: int
    book_name: str
    estimate_publish_date: date | None
    drama_type: str
    channel: str
    pitcher_id: int
    pitcher_name: str
    department_id: int
    department_name: str
    video_ids: tuple[int, ...] = ()


@dataclass
class MaterialSlice:
    stat_date: date
    ocean_material_id: int
    promotion_id: int
    promotion_name: str
    project_id: int
    project_name: str
    scope: str
    is_nobid: bool
    charge_mode: str
    series_id: int
    book_name: str
    estimate_publish_date: date | None
    video_id: int | None
    material_name: str
    material_type: str
    ownership: str
    file_url: str
    uploader_id: int | None
    uploader_name: str
    uploader_department_id: int | None
    uploader_department_name: str
    pitcher_id: int
    pitcher_name: str
    video_pitcher_ids: list[int] = field(default_factory=list)
    video_pitcher_names: list[str] = field(default_factory=list)
    stat_cost: Decimal = ZERO
    recovery: Decimal = ZERO
    show_cnt: int = 0
    click_cnt: int = 0
    convert_cnt: int = 0


@dataclass
class ProfitSlice:
    stat_date: date
    scope: str
    charge_mode: str
    drama_type: str
    platform: str
    department_id: int
    department_name: str
    pitcher_id: int
    pitcher_name: str
    stat_cost: Decimal = ZERO
    recovery: Decimal = ZERO


def match_video(
    material_id: int,
    material_name: str,
    project: ProjectCard,
    videos: dict[int, VideoCard],
) -> VideoCard | None:
    """先按素材库主键对上头条素材 id，再在本任务的视频里按名称对，最后在同剧里按名称对。"""
    direct = videos.get(material_id)
    if direct is not None:
        return direct
    name = material_name.strip()
    if not name:
        return None
    on_task = [videos[item] for item in project.video_ids if item in videos and videos[item].name == name]
    if len(on_task) == 1:
        return on_task[0]
    same_series = [
        video for video in videos.values() if video.name == name and video.series_id == project.series_id
    ]
    if len(same_series) == 1:
        return same_series[0]
    return None


def _add_metrics(target: MaterialSlice, raw: RawMaterial) -> None:
    target.stat_cost += raw.stat_cost
    target.recovery += raw.recovery
    target.show_cnt += raw.show_cnt
    target.click_cnt += raw.click_cnt
    target.convert_cnt += raw.convert_cnt


def build_slices(
    raws: Iterable[RawMaterial],
    projects: dict[int, ProjectCard],
    videos: dict[int, VideoCard],
) -> tuple[list[MaterialSlice], list[ProfitSlice]]:
    """对得上中台项目的小时合计写成素材行，再按利润维度加总。对不上的项目丢掉。"""
    materials: dict[tuple[Any, ...], MaterialSlice] = {}
    for raw in raws:
        project = projects.get(raw.project_id)
        if project is None:
            continue
        video = match_video(raw.material_id, raw.material_name, project, videos)
        if video is None:
            series_id = project.series_id
            book_name = project.book_name
            estimate = project.estimate_publish_date
            material_name = raw.material_name
            material_type = ""
            ownership = ""
            file_url = ""
            uploader_id = None
            uploader_name = ""
            uploader_department_id = None
            uploader_department_name = ""
            video_id = None
            pitcher_ids: list[int] = []
            pitcher_names: list[str] = []
        else:
            series_id = video.series_id
            book_name = video.book_name or project.book_name
            estimate = video.estimate_publish_date or project.estimate_publish_date
            material_name = video.name or raw.material_name
            material_type = video.material_type
            ownership = video.ownership
            file_url = video.file_url
            uploader_id = video.uploader_id
            uploader_name = video.uploader_name
            uploader_department_id = video.uploader_department_id
            uploader_department_name = video.uploader_department_name
            video_id = video.video_id
            pairs = sorted(zip(video.pitcher_ids, video.pitcher_names, strict=False))
            pitcher_ids = [item[0] for item in pairs]
            pitcher_names = [item[1] for item in pairs]
        key = (raw.stat_date, raw.material_id, raw.promotion_id, raw.project_id)
        current = materials.get(key)
        if current is None:
            current = MaterialSlice(
                stat_date=raw.stat_date,
                ocean_material_id=raw.material_id,
                promotion_id=raw.promotion_id,
                promotion_name=raw.promotion_name,
                project_id=raw.project_id,
                project_name=raw.project_name,
                scope=project.scope,
                is_nobid=is_nobid(project.scope, project.template_name),
                charge_mode=project.charge_mode,
                series_id=series_id,
                book_name=book_name,
                estimate_publish_date=estimate,
                video_id=video_id,
                material_name=material_name,
                material_type=material_type,
                ownership=ownership,
                file_url=file_url,
                uploader_id=uploader_id,
                uploader_name=uploader_name,
                uploader_department_id=uploader_department_id,
                uploader_department_name=uploader_department_name,
                pitcher_id=project.pitcher_id,
                pitcher_name=project.pitcher_name,
                video_pitcher_ids=pitcher_ids,
                video_pitcher_names=pitcher_names,
            )
            materials[key] = current
        _add_metrics(current, raw)
    profit: dict[tuple[Any, ...], ProfitSlice] = {}
    for row in materials.values():
        project = projects[row.project_id]
        key = (
            row.stat_date,
            project.scope,
            project.charge_mode,
            project.drama_type,
            platform_code(project.channel),
            project.department_id,
            project.pitcher_id,
        )
        bucket = profit.get(key)
        if bucket is None:
            bucket = ProfitSlice(
                stat_date=row.stat_date,
                scope=project.scope,
                charge_mode=project.charge_mode,
                drama_type=project.drama_type,
                platform=platform_code(project.channel),
                department_id=project.department_id,
                department_name=project.department_name,
                pitcher_id=project.pitcher_id,
                pitcher_name=project.pitcher_name,
            )
            profit[key] = bucket
        bucket.stat_cost += row.stat_cost
        bucket.recovery += row.recovery
    return list(materials.values()), list(profit.values())


def _mode_ok(row: ProfitSlice, mode: str) -> bool:
    if mode == "standard":
        return row.scope == "standard"
    if mode == "uni":
        return row.scope == "uni"
    if mode == "iaa":
        return row.charge_mode == "IAA"
    if mode == "iap":
        return row.charge_mode == "IAP"
    return True


def profit_visible(
    row: ProfitSlice,
    *,
    mode: str,
    drama_type: str | None,
    platform: str | None,
    department_ids: set[int] | None,
    pitcher_id: int | None,
) -> bool:
    if not _mode_ok(row, mode):
        return False
    if drama_type and row.drama_type != drama_type:
        return False
    if platform and row.platform != platform:
        return False
    if department_ids is not None and row.department_id not in department_ids:
        return False
    if pitcher_id is not None and row.pitcher_id != pitcher_id:
        return False
    return True


def _profit_metrics(cost: Decimal, recovery: Decimal, profit: Decimal) -> dict[str, float]:
    return {
        "stat_cost": money(cost),
        "recovery": money(recovery),
        "recovery_rate": ratio(recovery, cost),
        "profit": money(profit),
    }


def profit_table(
    rows: Iterable[ProfitSlice],
    spans: Iterable[RoiSpan],
    group: str,
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    """group：date、department、platform、pitcher。盈亏按天算完再加。"""
    chosen = list(spans)
    buckets: dict[Any, dict[str, Any]] = {}
    total_cost = ZERO
    total_recovery = ZERO
    total_profit = ZERO
    for row in rows:
        roi = roi_for(row.stat_date, chosen)
        day_profit = profit_amount(row.recovery, row.stat_cost, roi)
        if group == "date":
            key: Any = row.stat_date
        elif group == "department":
            key = (row.department_id, row.department_name)
        elif group == "platform":
            key = row.platform
        elif group == "pitcher":
            key = (row.pitcher_id, row.pitcher_name)
        else:
            raise ValueError("利润分组不支持")
        bucket = buckets.get(key)
        if bucket is None:
            bucket = {"cost": ZERO, "recovery": ZERO, "profit": ZERO, "key": key}
            buckets[key] = bucket
        bucket["cost"] += row.stat_cost
        bucket["recovery"] += row.recovery
        bucket["profit"] += day_profit
        total_cost += row.stat_cost
        total_recovery += row.recovery
        total_profit += day_profit
    out: list[dict[str, Any]] = []
    for bucket in buckets.values():
        item = _profit_metrics(bucket["cost"], bucket["recovery"], bucket["profit"])
        key = bucket["key"]
        if group == "date":
            item["stat_date"] = key.isoformat()
        elif group == "department":
            item["department_id"] = key[0]
            item["department_name"] = key[1]
        elif group == "platform":
            item["platform"] = key
            item["platform_name"] = PLATFORM_NAMES.get(key, key)
        else:
            item["pitcher_user_id"] = key[0]
            item["pitcher_name"] = key[1]
        out.append(item)
    return out, _profit_metrics(total_cost, total_recovery, total_profit)


def _sort(rows: list[dict[str, Any]], key: str, order: str) -> list[dict[str, Any]]:
    reverse = order != "asc"

    def value(row: dict[str, Any]) -> tuple[int, Any]:
        item = row.get(key)
        if item is None:
            return (1, 0)
        return (0, item)

    return sorted(rows, key=value, reverse=reverse)


def paged(rows: list[dict[str, Any]], summary: dict[str, Any], page: int, page_size: int, sort_by: str, sort_order: str) -> dict[str, Any]:
    ordered = _sort(rows, sort_by, sort_order)
    data = page_slice(ordered, PageParams(page=page, page_size=page_size))
    data["summary"] = summary
    return data


def _name_ok(book_name: str, query: str | None) -> bool:
    if not query:
        return True
    return query.strip() in book_name


def _age_ok(estimate: date | None, start: date, end: date, ages: Iterable[str]) -> bool:
    chosen = list(ages)
    if not chosen:
        return True
    return drama_band(estimate, start, end) in chosen


def _pitcher_text(ids: Iterable[int], names: Iterable[str], account_id: int, account_name: str) -> str:
    pairs = [(int(item_id), name) for item_id, name in zip(ids, names, strict=False) if name]
    if not pairs and account_name:
        pairs = [(account_id, account_name)]
    pairs.sort()
    return SEP.join(name for _, name in pairs)


def _spend_ok(row: MaterialSlice, pitcher_id: int | None, uploader_id: int | None) -> bool:
    if uploader_id is not None and row.uploader_id != uploader_id:
        return False
    if pitcher_id is None:
        return True
    return pitcher_id == row.pitcher_id or pitcher_id in row.video_pitcher_ids


def material_spend_table(
    rows: Iterable[MaterialSlice],
    *,
    pitcher_id: int | None,
    uploader_id: int | None,
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    """一天一条素材一行。对上素材库的按视频主键合并，否则按头条素材 id。"""
    buckets: dict[tuple[Any, ...], dict[str, Any]] = {}
    total = ZERO
    for row in rows:
        if not _spend_ok(row, pitcher_id, uploader_id):
            continue
        identity: Any = ("video", row.video_id) if row.video_id is not None else ("ocean", row.ocean_material_id)
        key = (row.stat_date, identity)
        bucket = buckets.get(key)
        if bucket is None:
            bucket = {
                "stat_date": row.stat_date.isoformat(),
                "video_id": row.video_id,
                "ocean_material_id": row.ocean_material_id,
                "material_name": row.material_name,
                "file_url": row.file_url,
                "series_id": row.series_id,
                "book_name": row.book_name,
                "material_type": row.material_type,
                "material_type_name": MATERIAL_TYPE_NAMES.get(row.material_type, ""),
                "ownership": row.ownership,
                "ownership_name": OWNERSHIP_NAMES.get(row.ownership, ""),
                "uploader_id": row.uploader_id,
                "uploader_name": row.uploader_name,
                "pitcher_names": _pitcher_text(
                    row.video_pitcher_ids, row.video_pitcher_names, row.pitcher_id, row.pitcher_name
                ),
                "cost": ZERO,
            }
            buckets[key] = bucket
        bucket["cost"] += row.stat_cost
        if row.ocean_material_id < bucket["ocean_material_id"]:
            bucket["ocean_material_id"] = row.ocean_material_id
        total += row.stat_cost
    out = []
    for bucket in buckets.values():
        cost = bucket.pop("cost")
        bucket["stat_cost"] = money(cost)
        out.append(bucket)
    return out, {"stat_cost": money(total)}


def material_detail_table(
    rows: Iterable[MaterialSlice],
    *,
    video_id: int | None,
    ocean_material_id: int | None,
    delivery: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """一条广告、一个头条素材一行。比率用合计后再除。"""
    buckets: dict[tuple[int, int], dict[str, Any]] = {}
    for row in rows:
        if video_id is not None:
            if row.video_id != video_id:
                continue
        elif row.ocean_material_id != ocean_material_id:
            continue
        if delivery == "standard" and row.scope != "standard":
            continue
        if delivery == "uni" and row.scope != "uni":
            continue
        key = (row.promotion_id, row.ocean_material_id)
        bucket = buckets.get(key)
        if bucket is None:
            bucket = {
                "promotion_id": row.promotion_id,
                "promotion_name": row.promotion_name,
                "project_id": row.project_id,
                "ocean_material_id": row.ocean_material_id,
                "pitcher_name": row.pitcher_name,
                "cost": ZERO,
                "show": 0,
                "click": 0,
                "convert": 0,
            }
            buckets[key] = bucket
        bucket["cost"] += row.stat_cost
        bucket["show"] += row.show_cnt
        bucket["click"] += row.click_cnt
        bucket["convert"] += row.convert_cnt
    out = []
    total_cost = ZERO
    for bucket in buckets.values():
        cost = bucket.pop("cost")
        show = bucket.pop("show")
        click = bucket.pop("click")
        convert = bucket.pop("convert")
        total_cost += cost
        bucket.update(
            {
                "stat_cost": money(cost),
                "show_cnt": show,
                "click_cnt": click,
                "ctr": ratio(click * 100, show, 2),
                "cpc": ratio(cost, click, 2),
                "cpm": ratio(cost * 1000, show, 2),
                "convert_cnt": convert,
                "conversion_rate": ratio(convert * 100, click, 2),
                "conversion_cost": ratio(cost, convert, 2),
            }
        )
        out.append(bucket)
    return out, {"stat_cost": money(total_cost)}


def group_avg_roi(rows: Iterable[MaterialSlice], department_id: int | None) -> float | None:
    """登录人所在部门、当前查询区间内，全部素材手的回收 / 消耗。没有这类行时为空。"""
    if department_id is None:
        return None
    cost = ZERO
    recovery = ZERO
    seen = False
    for row in rows:
        if row.uploader_department_id != department_id:
            continue
        seen = True
        cost += row.stat_cost
        recovery += row.recovery
    if not seen:
        return None
    return ratio(recovery, cost)


def editor_spend_table(
    rows: Iterable[MaterialSlice],
    *,
    uploader_id: int | None,
    department_id: int | None,
    avg_roi: float | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """一天一个素材手一行。总消耗（不含 nobid）= 总消耗 − 标准 nobid 消耗。"""
    buckets: dict[tuple[date, int], dict[str, Any]] = {}
    for row in rows:
        if row.uploader_id is None:
            continue
        if uploader_id is not None and row.uploader_id != uploader_id:
            continue
        if department_id is not None and row.uploader_department_id != department_id:
            continue
        key = (row.stat_date, row.uploader_id)
        bucket = buckets.get(key)
        if bucket is None:
            bucket = {
                "stat_date": row.stat_date.isoformat(),
                "uploader_id": row.uploader_id,
                "uploader_name": row.uploader_name,
                "total": ZERO,
                "standard_nobid": ZERO,
                "standard_non_nobid": ZERO,
                "uni_gmv": ZERO,
            }
            buckets[key] = bucket
        bucket["total"] += row.stat_cost
        if row.scope == "standard" and row.is_nobid:
            bucket["standard_nobid"] += row.stat_cost
        elif row.scope == "standard":
            bucket["standard_non_nobid"] += row.stat_cost
        if row.scope == "uni":
            bucket["uni_gmv"] += row.recovery
    out = []
    totals = {"total": ZERO, "standard_nobid": ZERO, "standard_non_nobid": ZERO, "uni_gmv": ZERO}
    for bucket in buckets.values():
        for name in totals:
            totals[name] += bucket[name]
        out.append(
            {
                "stat_date": bucket["stat_date"],
                "uploader_id": bucket["uploader_id"],
                "uploader_name": bucket["uploader_name"],
                "cost_ex_nobid": money(bucket["total"] - bucket["standard_nobid"]),
                "standard_non_nobid_cost": money(bucket["standard_non_nobid"]),
                "standard_nobid_cost": money(bucket["standard_nobid"]),
                "uni_gmv": money(bucket["uni_gmv"]),
                "group_avg_roi": avg_roi,
                "stat_cost": money(bucket["total"]),
            }
        )
    summary = {
        "cost_ex_nobid": money(totals["total"] - totals["standard_nobid"]),
        "standard_non_nobid_cost": money(totals["standard_non_nobid"]),
        "standard_nobid_cost": money(totals["standard_nobid"]),
        "uni_gmv": money(totals["uni_gmv"]),
        "group_avg_roi": None,
        "stat_cost": money(totals["total"]),
    }
    return out, summary


def drama_spend_table(
    rows: Iterable[MaterialSlice],
    library_counts: dict[int, int],
    *,
    start: date,
    end: date,
    series_name: str | None,
    ages: Iterable[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """一部剧一行。素材数是视频库里这部剧的条数，不是有消耗的条数。"""
    buckets: dict[int, dict[str, Any]] = {}
    for row in rows:
        if not _name_ok(row.book_name, series_name) or not _age_ok(row.estimate_publish_date, start, end, ages):
            continue
        bucket = buckets.get(row.series_id)
        if bucket is None:
            bucket = {
                "series_id": row.series_id,
                "book_name": row.book_name,
                "material_count": int(library_counts.get(row.series_id, 0)),
                "cost": ZERO,
            }
            buckets[row.series_id] = bucket
        bucket["cost"] += row.stat_cost
    out = []
    total_cost = ZERO
    total_count = 0
    for bucket in buckets.values():
        total_cost += bucket["cost"]
        total_count += bucket["material_count"]
        out.append(
            {
                "series_id": bucket["series_id"],
                "book_name": bucket["book_name"],
                "material_count": bucket["material_count"],
                "stat_cost": money(bucket["cost"]),
            }
        )
    return out, {"material_count": total_count, "stat_cost": money(total_cost)}


def drama_editor_table(
    rows: Iterable[MaterialSlice],
    library_counts: dict[int, int],
    *,
    start: date,
    end: date,
    series_name: str | None,
    uploader_id: int | None,
    ages: Iterable[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """一部剧、一个素材手一行。素材数仍是这部剧在视频库的条数。合计按剧去重。"""
    buckets: dict[tuple[int, int], dict[str, Any]] = {}
    for row in rows:
        if row.uploader_id is None:
            continue
        if uploader_id is not None and row.uploader_id != uploader_id:
            continue
        if not _name_ok(row.book_name, series_name) or not _age_ok(row.estimate_publish_date, start, end, ages):
            continue
        key = (row.series_id, row.uploader_id)
        bucket = buckets.get(key)
        if bucket is None:
            bucket = {
                "series_id": row.series_id,
                "book_name": row.book_name,
                "uploader_id": row.uploader_id,
                "uploader_name": row.uploader_name,
                "material_count": int(library_counts.get(row.series_id, 0)),
                "cost": ZERO,
            }
            buckets[key] = bucket
        bucket["cost"] += row.stat_cost
    out = []
    seen_counts: dict[int, int] = {}
    total_cost = ZERO
    for bucket in buckets.values():
        seen_counts[bucket["series_id"]] = bucket["material_count"]
        total_cost += bucket["cost"]
        out.append(
            {
                "series_id": bucket["series_id"],
                "book_name": bucket["book_name"],
                "uploader_id": bucket["uploader_id"],
                "uploader_name": bucket["uploader_name"],
                "material_count": bucket["material_count"],
                "stat_cost": money(bucket["cost"]),
            }
        )
    return out, {"material_count": sum(seen_counts.values()), "stat_cost": money(total_cost)}


def video_spend_table(
    rows: Iterable[MaterialSlice],
    *,
    start: date,
    end: date,
    series_name: str | None,
    uploader_id: int | None,
    ages: Iterable[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """一条素材一行。素材数合计是行数。"""
    buckets: dict[Any, dict[str, Any]] = {}
    for row in rows:
        if uploader_id is not None and row.uploader_id != uploader_id:
            continue
        if not _name_ok(row.book_name, series_name) or not _age_ok(row.estimate_publish_date, start, end, ages):
            continue
        identity: Any = ("video", row.video_id) if row.video_id is not None else ("ocean", row.ocean_material_id)
        bucket = buckets.get(identity)
        if bucket is None:
            bucket = {
                "video_id": row.video_id,
                "ocean_material_id": row.ocean_material_id,
                "file_url": row.file_url,
                "series_id": row.series_id,
                "book_name": row.book_name,
                "uploader_id": row.uploader_id,
                "uploader_name": row.uploader_name,
                "material_name": row.material_name,
                "cost": ZERO,
            }
            buckets[identity] = bucket
        bucket["cost"] += row.stat_cost
    out = []
    total = ZERO
    for bucket in buckets.values():
        total += bucket["cost"]
        out.append(
            {
                "video_id": bucket["video_id"],
                "ocean_material_id": bucket["ocean_material_id"],
                "file_url": bucket["file_url"],
                "series_id": bucket["series_id"],
                "book_name": bucket["book_name"],
                "uploader_id": bucket["uploader_id"],
                "uploader_name": bucket["uploader_name"],
                "material_name": bucket["material_name"],
                "stat_cost": money(bucket["cost"]),
            }
        )
    return out, {"material_count": len(out), "stat_cost": money(total)}


@dataclass(frozen=True)
class SeriesCard:
    series_id: int
    book_name: str
    estimate_publish_date: date


def nb_table(
    series: Iterable[SeriesCard],
    nb_counts: dict[int, int],
    *,
    series_name: str | None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """预估可投日已在查询里筛过。素材数只数 NB 计划挂上的视频，可以为 0。"""
    out = []
    total = 0
    for row in series:
        if not _name_ok(row.book_name, series_name):
            continue
        count = int(nb_counts.get(row.series_id, 0))
        total += count
        out.append(
            {
                "series_id": row.series_id,
                "book_name": row.book_name,
                "estimate_publish_date": row.estimate_publish_date.isoformat(),
                "material_count": count,
            }
        )
    return out, {"material_count": total}


def editor_stat_table(
    rows: Iterable[MaterialSlice],
    *,
    uploader_id: int | None,
    department_id: int | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """一天一个素材手一行。新剧数要求预估可投日等于这一天，且这一天有消耗。"""
    buckets: dict[tuple[date, int], dict[str, Any]] = {}
    for row in rows:
        if row.uploader_id is None or row.stat_cost <= 0:
            continue
        if uploader_id is not None and row.uploader_id != uploader_id:
            continue
        if department_id is not None and row.uploader_department_id != department_id:
            continue
        key = (row.stat_date, row.uploader_id)
        bucket = buckets.get(key)
        if bucket is None:
            bucket = {
                "stat_date": row.stat_date.isoformat(),
                "uploader_id": row.uploader_id,
                "uploader_name": row.uploader_name,
                "new": set(),
                "dramas": set(),
                "videos": set(),
                "cost": ZERO,
            }
            buckets[key] = bucket
        bucket["dramas"].add(row.series_id)
        if row.estimate_publish_date == row.stat_date:
            bucket["new"].add(row.series_id)
        video_key = ("video", row.video_id) if row.video_id is not None else ("ocean", row.ocean_material_id)
        bucket["videos"].add(video_key)
        bucket["cost"] += row.stat_cost
    out = []
    summary = {"new_drama_count": 0, "drama_count": 0, "material_count": 0, "stat_cost": ZERO}
    for bucket in buckets.values():
        item = {
            "stat_date": bucket["stat_date"],
            "uploader_id": bucket["uploader_id"],
            "uploader_name": bucket["uploader_name"],
            "new_drama_count": len(bucket["new"]),
            "drama_count": len(bucket["dramas"]),
            "material_count": len(bucket["videos"]),
            "stat_cost": money(bucket["cost"]),
        }
        summary["new_drama_count"] += item["new_drama_count"]
        summary["drama_count"] += item["drama_count"]
        summary["material_count"] += item["material_count"]
        summary["stat_cost"] += bucket["cost"]
        out.append(item)
    summary["stat_cost"] = money(summary["stat_cost"])
    return out, summary
