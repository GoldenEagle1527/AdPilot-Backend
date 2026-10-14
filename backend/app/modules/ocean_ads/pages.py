"""项目、广告、素材、全域项目列表，以及批量改状态和项目预算。"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.pagination import PageParams, page_data
from app.modules.account.model import (
    AdvertiserAccount,
    DeliverySubject,
    DouyinAccount,
    OeMaterialReport,
    OeProject,
    OePromotion,
)
from app.modules.material.model import ManhuaSeries
from app.modules.material_video.model import MaterialVideo
from app.modules.ocean_ads.schema import (
    MaterialQuery,
    ProjectBatchWrite,
    ProjectBudgetWrite,
    ProjectQuery,
    PromotionBatchWrite,
    PromotionNameQuery,
    PromotionQuery,
    UniProjectQuery,
)
from app.modules.ocean_ads.service import _display_name, _money, _rate, _require_pitcher, effect_numbers
from app.modules.oceanengine.client import OceanEngineError
from app.modules.system_admin.domain.models import User
from app.modules.oceanengine.runtime import _access_token, get_ocean_client
from app.modules.system_admin.domain.scope import resolve_data_scope, owner_match

_OCEAN_STATUS_BATCH = 10


def project_status_label(opt_status: str) -> str:
    """库里 ENABLE/DISABLE，页面传开启/暂停。"""
    return "开启" if opt_status == "ENABLE" else "暂停"


def accepted_delete_ids(remote: dict[str, Any], id_key: str, requested: list[int]) -> tuple[list[int], list[str]]:
    """只有巨量返回的成功 id 才算删成。没出现在成功列表里的，本库不删。"""
    data = remote.get("data") if isinstance(remote.get("data"), dict) else {}
    failed_ids: set[int] = set()
    messages: list[str] = []
    for item in data.get("errors") or []:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("project_id", item.get("promotion_id"))
        if raw_id is not None:
            failed_ids.add(int(raw_id))
        messages.append(str(item.get("error_message") or raw_id or "删除失败"))
    ok = [int(item) for item in data.get(id_key) or [] if int(item) not in failed_ids]
    ok_set = set(ok)
    for item in requested:
        if item not in ok_set and item not in failed_ids:
            messages.append(f"{item} 未返回删除成功")
    return [item for item in requested if item in ok_set], messages


def accepted_status_ids(remote: dict[str, Any], id_key: str, requested: list[int]) -> tuple[list[int], list[str]]:
    """回包里的 id 列表是成功的。errors 里的 id 不算成功。两边都空则这批都成功。"""
    data = remote.get("data") if isinstance(remote.get("data"), dict) else {}
    failed_ids: set[int] = set()
    messages: list[str] = []
    for item in data.get("errors") or []:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("project_id", item.get("promotion_id"))
        if raw_id is not None:
            failed_ids.add(int(raw_id))
        messages.append(str(item.get("error_message") or raw_id or "更新失败"))
    ok = [int(item) for item in data.get(id_key) or [] if int(item) not in failed_ids]
    if messages:
        return ok, messages
    return ok or [item for item in requested if item not in failed_ids], messages


def batch_status(action: str) -> str | None:
    """开启、暂停改开关。删除返回空，调用方做软删除。"""
    if action == "开启":
        return "ENABLE"
    if action == "暂停":
        return "DISABLE"
    return None


def promotion_status_label(opt_status: str, project_opt_status: str | None) -> str:
    """父项目暂停时，广告开关开着也显示已被项目暂停。"""
    if project_opt_status == "DISABLE":
        return "已被项目暂停"
    if opt_status == "DISABLE":
        return "已暂停"
    return "投放中"


def _budget(template: dict | None) -> str | None:
    """读项目上已经存下的预算。没存则空。"""
    if not isinstance(template, dict):
        return None
    setting = template.get("delivery_setting")
    if not isinstance(setting, dict) or setting.get("budget") is None:
        return None
    try:
        return _money(Decimal(str(setting["budget"])))
    except InvalidOperation:
        return None


_COUNT_SORT = {
    "project_id",
    "promotion_id",
    "material_id",
    "account_id",
    "book_id",
    "show_cnt",
    "click_cnt",
    "convert_cnt",
    "active",
}


def _sort_value(row: dict[str, Any], name: str) -> tuple[int, Decimal | int]:
    """空比率排在有数的后面。编号和次数按整数排，金额和比率按数字排。"""
    value = row[name]
    if value is None:
        return (1, Decimal(0))
    if name in _COUNT_SORT:
        return (0, int(value))
    return (0, Decimal(str(value)))


def _seven(metric: Any) -> tuple[Decimal, Decimal, Decimal, int, int, int, int]:
    """消耗、当日收益、总收益、展示、点击、转化、激活。没有报表行时全是 0。"""
    if metric is None:
        return (Decimal(0), Decimal(0), Decimal(0), 0, 0, 0, 0)
    return (
        Decimal(metric[0]),
        Decimal(metric[1]),
        Decimal(metric[2]),
        int(metric[3]),
        int(metric[4]),
        int(metric[5]),
        int(metric[6]),
    )


def _aweme_from_template(template: dict | None) -> str | None:
    """创建项目时写在 native_setting 里的抖音号。"""
    setting = template.get("native_setting") if isinstance(template, dict) else None
    if not isinstance(setting, dict) or setting.get("aweme_id") is None:
        return None
    text = str(setting.get("aweme_id")).strip()
    return text or None


def _labels(values: list[str | None]) -> str | None:
    """同一项目下不重复的名称，按出现顺序用顿号接上。"""
    found: list[str] = []
    for value in values:
        text = "" if value is None else str(value).strip()
        if text and text not in found:
            found.append(text)
    return "、".join(found) or None


def _has_series(series_id: int):
    """项目下有这条短剧的未删除广告。短剧 id 是 manhua_series.id。"""
    return (
        select(OePromotion.id)
        .where(
            OePromotion.ocean_project_id == OeProject.ocean_project_id,
            OePromotion.series_id == series_id,
            OePromotion.is_deleted == 0,
        )
        .exists()
    )


def _like(raw: str) -> str:
    escaped = raw.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _day_between(query_start: Any, query_end: Any) -> list[Any]:
    if query_start is None or query_end is None:
        return []
    day_text = func.substr(OeMaterialReport.stat_time_hour, 1, 10)
    return [day_text >= query_start.isoformat(), day_text <= query_end.isoformat()]


async def list_projects(
    session: AsyncSession, query: ProjectQuery, principal: dict[str, Any]
) -> dict[str, Any]:
    """标准项目和全域项目都列出。账户必须在当前登录人的数据范围内。"""
    if query.pitcher_user_id is not None:
        await _require_pitcher(session, query.pitcher_user_id)
    scope = await resolve_data_scope(session, principal)
    filters = [
        OeProject.is_deleted == 0,
        OeProject.create_message.is_(None),
        DeliverySubject.is_deleted == 0,
        AdvertiserAccount.is_deleted == 0,
        owner_match(AdvertiserAccount.pitcher_user_id, int(principal["id"]), scope),
    ]
    if query.charge_mode is not None:
        filters.append(DeliverySubject.charge_mode == query.charge_mode)
    if query.series_id is not None:
        filters.append(_has_series(query.series_id))
    if query.project_id is not None:
        filters.append(OeProject.ocean_project_id == query.project_id)
    if query.project_status is not None:
        filters.append(OeProject.opt_status == ("ENABLE" if query.project_status == "开启" else "DISABLE"))
    if query.account_id is not None:
        filters.append(OeProject.advertiser_id == query.account_id)
    if query.pitcher_user_id is not None:
        filters.append(AdvertiserAccount.pitcher_user_id == query.pitcher_user_id)
    project_name = (query.project_name or "").strip()
    if project_name:
        filters.append(OeProject.name.ilike(_like(project_name), escape="\\"))
    account_name = (query.account_name or "").strip()
    if account_name:
        pattern = _like(account_name)
        filters.append(
            or_(
                AdvertiserAccount.name.ilike(pattern, escape="\\"),
                AdvertiserAccount.local_name.ilike(pattern, escape="\\"),
            )
        )
    found = list(
        (
            await session.execute(
                select(OeProject, AdvertiserAccount)
                .join(DeliverySubject, OeProject.subject_id == DeliverySubject.id)
                .join(AdvertiserAccount, AdvertiserAccount.advertiser_id == OeProject.advertiser_id)
                .where(*filters)
            )
        ).all()
    )
    project_ids = [int(project.ocean_project_id) for project, _account in found]
    metrics = await _sum_by_project(session, project_ids, query.date_start, query.date_end)
    links = await _links_by_project(session, project_ids)
    rows = []
    for project, account in found:
        cost, today, total, shows, clicks, converts, actives = _seven(
            metrics.get(int(project.ocean_project_id))
        )
        rows.append(
            {
                "project_id": int(project.ocean_project_id),
                "project_name": project.name,
                "project_status": project_status_label(project.opt_status),
                "account_id": int(account.advertiser_id),
                "account_name": _display_name(account.name, account.local_name),
                "budget": _budget(project.template),
                "promotion_links": links.get(int(project.ocean_project_id), []),
                **effect_numbers(cost, today, total, shows, clicks, converts, actives),
            }
        )
    rows.sort(key=lambda row: _sort_value(row, query.sort_by), reverse=query.sort_order == "desc")
    params = PageParams(page=query.page, page_size=query.page_size)
    return page_data(rows[params.offset : params.offset + params.page_size], len(rows), params)


async def _links_by_project(session: AsyncSession, project_ids: list[int]) -> dict[int, list[str]]:
    """一个项目下面未删除广告的完整链接，去重后按出现顺序。"""
    if not project_ids:
        return {}
    rows = await session.execute(
        select(OePromotion.ocean_project_id, OePromotion.promotion_links).where(
            OePromotion.ocean_project_id.in_(project_ids),
            OePromotion.is_deleted == 0,
        )
    )
    grouped: dict[int, list[str]] = {}
    for project_id, raw_links in rows.all():
        if project_id is None:
            continue
        bucket = grouped.setdefault(int(project_id), [])
        for link in raw_links or []:
            text = str(link).strip()
            if text and text not in bucket:
                bucket.append(text)
    return grouped


async def batch_projects(
    session: AsyncSession, body: ProjectBatchWrite, principal: dict[str, Any]
) -> dict[str, Any]:
    """批量开启、暂停或删除。只改当前登录人能看的项目，下面未删除的广告跟着改。删除先通知巨量。"""
    scope = await resolve_data_scope(session, principal)
    projects = list(
        (
            await session.scalars(
                select(OeProject)
                .join(AdvertiserAccount, AdvertiserAccount.advertiser_id == OeProject.advertiser_id)
                .where(
                    OeProject.ocean_project_id.in_(body.project_ids),
                    OeProject.is_deleted == 0,
                    AdvertiserAccount.is_deleted == 0,
                    owner_match(AdvertiserAccount.pitcher_user_id, int(principal["id"]), scope),
                )
            )
        )
        .unique()
        .all()
    )
    project_ids = [int(project.ocean_project_id) for project in projects]
    promotions: list[OePromotion] = []
    if project_ids:
        promotions = list(
            (
                await session.scalars(
                    select(OePromotion).where(
                        OePromotion.ocean_project_id.in_(project_ids),
                        OePromotion.is_deleted == 0,
                    )
                )
            ).all()
        )
    status = batch_status(body.action)
    if status is None:
        remote_projects = [project for project in projects if not project.create_message]
        local_ids = {int(project.ocean_project_id) for project in projects if project.create_message}
        accepted_projects, messages = await _push_grouped_delete(
            session,
            _ids_by_advertiser(
                [(int(project.advertiser_id), int(project.ocean_project_id)) for project in remote_projects]
            ),
            id_key="project_id",
            kind="project",
        )
        accepted_projects |= local_ids
        for project in projects:
            if int(project.ocean_project_id) in accepted_projects:
                project.mark_deleted()
        changed_ads = 0
        for promotion in promotions:
            if int(promotion.ocean_project_id or 0) in local_ids:
                promotion.mark_deleted()
                changed_ads += 1
        ads = [row for row in promotions if int(row.ocean_project_id or 0) in accepted_projects - local_ids]
        accepted_ads, ad_messages = await _push_grouped_delete(
            session,
            _ids_by_advertiser([(int(row.advertiser_id), int(row.promotion_id)) for row in ads]),
            id_key="promotion_id",
            kind="promotion",
        )
        messages.extend(ad_messages)
        for promotion in ads:
            if int(promotion.promotion_id) in accepted_ads:
                promotion.mark_deleted()
                changed_ads += 1
        await session.flush()
        if messages:
            await session.commit()
            raise ApiError(502, "；".join(messages))
        return {"project_ids": sorted(accepted_projects), "promotion_count": changed_ads}
    remote_projects = [project for project in projects if not project.create_message]
    local_ids = {int(project.ocean_project_id) for project in projects if project.create_message}
    accepted_projects, messages = await _push_grouped_status(
        session,
        _ids_by_advertiser(
            [(int(project.advertiser_id), int(project.ocean_project_id)) for project in remote_projects]
        ),
        status,
        id_key="project_id",
        kind="project",
    )
    accepted_projects |= local_ids
    for project in projects:
        if int(project.ocean_project_id) in accepted_projects:
            project.opt_status = status
    changed_ads = 0
    for promotion in promotions:
        if int(promotion.ocean_project_id or 0) in local_ids:
            promotion.opt_status = status
            changed_ads += 1
    ads = [row for row in promotions if int(row.ocean_project_id or 0) in accepted_projects - local_ids]
    accepted_ads, ad_messages = await _push_grouped_status(
        session,
        _ids_by_advertiser([(int(row.advertiser_id), int(row.promotion_id)) for row in ads]),
        status,
        id_key="promotion_id",
        kind="promotion",
    )
    messages.extend(ad_messages)
    for promotion in ads:
        if int(promotion.promotion_id) in accepted_ads:
            promotion.opt_status = status
            changed_ads += 1
    await session.flush()
    if messages:
        await session.commit()
        raise ApiError(502, "；".join(messages))
    return {"project_ids": sorted(accepted_projects), "promotion_count": changed_ads}


def _ids_by_advertiser(pairs: list[tuple[int, int]]) -> dict[int, list[int]]:
    grouped: dict[int, list[int]] = {}
    for advertiser_id, item_id in pairs:
        grouped.setdefault(advertiser_id, []).append(item_id)
    return grouped


async def _push_grouped_status(
    session: AsyncSession,
    grouped: dict[int, list[int]],
    opt_status: str,
    *,
    id_key: str,
    kind: str,
) -> tuple[set[int], list[str]]:
    """按账户调用巨量启停。一次最多 10 条。"""
    if not grouped:
        return set(), []
    client = get_ocean_client()
    token = await _access_token(session)
    accepted: set[int] = set()
    messages: list[str] = []
    for advertiser_id, item_ids in grouped.items():
        for start in range(0, len(item_ids), _OCEAN_STATUS_BATCH):
            chunk = item_ids[start : start + _OCEAN_STATUS_BATCH]
            body = {
                "advertiser_id": advertiser_id,
                "data": [{id_key: item_id, "opt_status": opt_status} for item_id in chunk],
            }
            try:
                if kind == "project":
                    remote = await client.update_project_status(token, body)
                else:
                    remote = await client.update_promotion_status(token, body)
            except OceanEngineError as exc:
                messages.append(str(exc))
                continue
            ok, failed = accepted_status_ids(remote, f"{id_key}s", chunk)
            accepted.update(ok)
            messages.extend(failed)
    return accepted, messages


async def _push_grouped_delete(
    session: AsyncSession,
    grouped: dict[int, list[int]],
    *,
    id_key: str,
    kind: str,
) -> tuple[set[int], list[str]]:
    """按账户通知巨量删除。一次最多 10 条。巨量接受的才由调用方在本库软删。"""
    if not grouped:
        return set(), []
    client = get_ocean_client()
    token = await _access_token(session)
    accepted: set[int] = set()
    messages: list[str] = []
    for advertiser_id, item_ids in grouped.items():
        for start in range(0, len(item_ids), _OCEAN_STATUS_BATCH):
            chunk = item_ids[start : start + _OCEAN_STATUS_BATCH]
            body = {"advertiser_id": advertiser_id, f"{id_key}s": chunk}
            try:
                if kind == "project":
                    remote = await client.delete_projects(token, body)
                else:
                    remote = await client.delete_promotions(token, body)
            except OceanEngineError as exc:
                messages.append(str(exc))
                continue
            ok, failed = accepted_delete_ids(remote, f"{id_key}s", chunk)
            accepted.update(ok)
            messages.extend(failed)
    return accepted, messages


async def _sum_by_project(session: AsyncSession, project_ids: list[int], start: Any, end: Any) -> dict[int, Any]:
    if not project_ids:
        return {}
    stmt = (
        select(
            OeMaterialReport.cdp_project_id,
            func.coalesce(func.sum(OeMaterialReport.stat_cost), 0),
            func.coalesce(func.sum(OeMaterialReport.attribution_billing_game_in_app_ltv_1day), 0),
            func.coalesce(func.sum(OeMaterialReport.stat_pay_amount), 0),
            func.coalesce(func.sum(OeMaterialReport.show_cnt), 0),
            func.coalesce(func.sum(OeMaterialReport.click_cnt), 0),
            func.coalesce(func.sum(OeMaterialReport.convert_cnt), 0),
            func.coalesce(func.sum(OeMaterialReport.active), 0),
        )
        .where(OeMaterialReport.cdp_project_id.in_(project_ids), *_day_between(start, end))
        .group_by(OeMaterialReport.cdp_project_id)
    )
    rows = await session.execute(stmt)
    return {int(project_id): rest for project_id, *rest in rows.all()}


async def list_promotions(
    session: AsyncSession, query: PromotionQuery, principal: dict[str, Any]
) -> dict[str, Any]:
    """广告列表。推广外链按完整链接精确匹配。短剧名称模糊匹配剧库。"""
    if query.pitcher_user_id is not None:
        await _require_pitcher(session, query.pitcher_user_id)
    scope = await resolve_data_scope(session, principal)
    filters = [
        OePromotion.is_deleted == 0,
        AdvertiserAccount.is_deleted == 0,
        owner_match(AdvertiserAccount.pitcher_user_id, int(principal["id"]), scope),
    ]
    if query.promotion_id is not None:
        filters.append(OePromotion.promotion_id == query.promotion_id)
    if query.account_id is not None:
        filters.append(OePromotion.advertiser_id == query.account_id)
    if query.project_id is not None:
        filters.append(OePromotion.ocean_project_id == query.project_id)
    if query.series_id is not None:
        filters.append(OePromotion.series_id == query.series_id)
    if query.pitcher_user_id is not None:
        filters.append(AdvertiserAccount.pitcher_user_id == query.pitcher_user_id)
    if query.charge_mode is not None:
        filters.append(DeliverySubject.charge_mode == query.charge_mode)
    promotion_name = (query.promotion_name or "").strip()
    if promotion_name:
        filters.append(OePromotion.name == promotion_name)
    project_name = (query.project_name or "").strip()
    if project_name:
        filters.append(OeProject.name.ilike(_like(project_name), escape="\\"))
    promotion_link = (query.promotion_link or "").strip()
    if promotion_link:
        filters.append(OePromotion.promotion_links.any(promotion_link))
    series_name = (query.series_name or "").strip()
    if series_name:
        filters.append(ManhuaSeries.book_name.ilike(_like(series_name), escape="\\"))
    account_name = (query.account_name or "").strip()
    if account_name:
        pattern = _like(account_name)
        filters.append(
            or_(
                AdvertiserAccount.name.ilike(pattern, escape="\\"),
                AdvertiserAccount.local_name.ilike(pattern, escape="\\"),
            )
        )
    stmt = (
        select(OePromotion, AdvertiserAccount, OeProject, ManhuaSeries)
        .join(AdvertiserAccount, AdvertiserAccount.advertiser_id == OePromotion.advertiser_id)
        .outerjoin(OeProject, OeProject.ocean_project_id == OePromotion.ocean_project_id)
        .outerjoin(DeliverySubject, DeliverySubject.id == OeProject.subject_id)
        .outerjoin(ManhuaSeries, ManhuaSeries.id == OePromotion.series_id)
        .where(*filters)
    )
    found = list((await session.execute(stmt)).all())
    promotion_ids = [int(row.promotion_id) for row, _account, _project, _series in found]
    metrics = await _sum_by_promotion(session, promotion_ids, query.date_start, query.date_end)
    rows = []
    for promotion, account, project, series in found:
        project_opt = None if project is None else project.opt_status
        status = promotion_status_label(promotion.opt_status, project_opt)
        if query.promotion_status is not None and status != query.promotion_status:
            continue
        cost, today, total, shows, clicks, converts, actives = _seven(
            metrics.get(int(promotion.promotion_id))
        )
        rows.append(
            {
                "promotion_id": int(promotion.promotion_id),
                "promotion_name": promotion.name or "",
                "promotion_status": status,
                "project_id": None if promotion.ocean_project_id is None else int(promotion.ocean_project_id),
                "project_name": None if project is None else project.name,
                "series_name": None if series is None else series.book_name,
                "book_id": None if series is None else int(series.book_id),
                "account_id": int(account.advertiser_id),
                "account_name": _display_name(account.name, account.local_name),
                "promotion_links": list(promotion.promotion_links or []),
                "budget": None if promotion.budget is None else _money(Decimal(promotion.budget)),
                "reject_reasons": [],
                **effect_numbers(cost, today, total, shows, clicks, converts, actives),
            }
        )
    rows.sort(key=lambda row: _sort_value(row, query.sort_by), reverse=query.sort_order == "desc")
    params = PageParams(page=query.page, page_size=query.page_size)
    page_rows = rows[params.offset : params.offset + params.page_size]
    await _fill_reject_reasons(session, page_rows)
    return page_data(page_rows, len(rows), params)


async def list_promotion_names(
    session: AsyncSession, query: PromotionNameQuery, principal: dict[str, Any]
) -> dict[str, Any]:
    """广告名称下拉。未删除、当前登录人能看到的广告名。产品说名称不重复。"""
    scope = await resolve_data_scope(session, principal)
    names = (
        select(OePromotion.name)
        .join(AdvertiserAccount, AdvertiserAccount.advertiser_id == OePromotion.advertiser_id)
        .where(
            OePromotion.is_deleted == 0,
            AdvertiserAccount.is_deleted == 0,
            owner_match(AdvertiserAccount.pitcher_user_id, int(principal["id"]), scope),
            OePromotion.name.is_not(None),
            OePromotion.name != "",
        )
        .distinct()
    )
    total = int(await session.scalar(select(func.count()).select_from(names.subquery())) or 0)
    params = PageParams(page=query.page, page_size=query.page_size)
    found = await session.scalars(names.order_by(OePromotion.name).offset(params.offset).limit(params.page_size))
    return page_data([{"promotion_name": name} for name in found.all()], total, params)


async def _sum_by_promotion(session: AsyncSession, promotion_ids: list[int], start: Any, end: Any) -> dict[int, Any]:
    if not promotion_ids:
        return {}
    stmt = (
        select(
            OeMaterialReport.cdp_promotion_id,
            func.coalesce(func.sum(OeMaterialReport.stat_cost), 0),
            func.coalesce(func.sum(OeMaterialReport.attribution_billing_game_in_app_ltv_1day), 0),
            func.coalesce(func.sum(OeMaterialReport.stat_pay_amount), 0),
            func.coalesce(func.sum(OeMaterialReport.show_cnt), 0),
            func.coalesce(func.sum(OeMaterialReport.click_cnt), 0),
            func.coalesce(func.sum(OeMaterialReport.convert_cnt), 0),
            func.coalesce(func.sum(OeMaterialReport.active), 0),
        )
        .where(OeMaterialReport.cdp_promotion_id.in_(promotion_ids), *_day_between(start, end))
        .group_by(OeMaterialReport.cdp_promotion_id)
    )
    rows = await session.execute(stmt)
    return {int(promotion_id): rest for promotion_id, *rest in rows.all()}


async def list_materials(
    session: AsyncSession, query: MaterialQuery, principal: dict[str, Any]
) -> dict[str, Any]:
    """素材页按某一天加总。投手须带短剧投手标签。所属项目或广告已软删除的不显示。"""
    if query.pitcher_user_id is not None:
        await _require_pitcher(session, query.pitcher_user_id)
    scope = await resolve_data_scope(session, principal)
    day = query.stat_date.isoformat()
    day_text = func.substr(OeMaterialReport.stat_time_hour, 1, 10)
    filters = [
        day_text == day,
        AdvertiserAccount.is_deleted == 0,
        owner_match(AdvertiserAccount.pitcher_user_id, int(principal["id"]), scope),
        ~select(OeProject.id)
        .where(
            OeProject.ocean_project_id == OeMaterialReport.cdp_project_id,
            OeProject.is_deleted == 1,
        )
        .exists(),
        ~select(OePromotion.id)
        .where(
            OePromotion.advertiser_id == OeMaterialReport.advertiser_id,
            OePromotion.promotion_id == OeMaterialReport.cdp_promotion_id,
            OePromotion.is_deleted == 1,
        )
        .correlate_except(OePromotion)
        .exists(),
    ]
    if query.account_id is not None:
        filters.append(OeMaterialReport.advertiser_id == query.account_id)
    if query.pitcher_user_id is not None:
        filters.append(AdvertiserAccount.pitcher_user_id == query.pitcher_user_id)
    if query.promotion_id is not None:
        filters.append(OeMaterialReport.cdp_promotion_id == query.promotion_id)
    if query.material_id is not None:
        filters.append(MaterialVideo.ocean_material_id == query.material_id)
    account_name = (query.account_name or "").strip()
    if account_name:
        pattern = _like(account_name)
        filters.append(
            or_(
                AdvertiserAccount.name.ilike(pattern, escape="\\"),
                AdvertiserAccount.local_name.ilike(pattern, escape="\\"),
            )
        )
    stmt = (
        select(
            func.max(MaterialVideo.ocean_material_id),
            func.min(MaterialVideo.id),
            func.max(OeMaterialReport.ad_platform_material_name),
            func.max(OePromotion.promotion_id),
            func.max(OeMaterialReport.cdp_promotion_name),
            OeMaterialReport.cdp_project_id,
            func.max(OeMaterialReport.cdp_project_name),
            OeMaterialReport.advertiser_id,
            func.max(AdvertiserAccount.name),
            func.max(AdvertiserAccount.local_name),
            func.coalesce(func.sum(OeMaterialReport.stat_cost), 0),
            func.coalesce(func.sum(OeMaterialReport.show_cnt), 0),
            func.coalesce(func.sum(OeMaterialReport.click_cnt), 0),
            func.coalesce(func.sum(OeMaterialReport.convert_cnt), 0),
        )
        .join(AdvertiserAccount, AdvertiserAccount.advertiser_id == OeMaterialReport.advertiser_id)
        .outerjoin(
            MaterialVideo,
            and_(
                MaterialVideo.ocean_material_id == OeMaterialReport.material_id,
                MaterialVideo.is_deleted == 0,
            ),
        )
        .outerjoin(
            OePromotion,
            and_(
                OePromotion.advertiser_id == OeMaterialReport.advertiser_id,
                OePromotion.promotion_id == OeMaterialReport.cdp_promotion_id,
                OePromotion.is_deleted == 0,
            ),
        )
        .where(*filters)
        .group_by(
            OeMaterialReport.material_id,
            OeMaterialReport.cdp_promotion_id,
            OeMaterialReport.cdp_project_id,
            OeMaterialReport.advertiser_id,
        )
    )
    found = list((await session.execute(stmt)).all())
    rows = [
        {
            "material_id": None if material_id is None else int(material_id),
            "video_id": None if video_id is None else int(video_id),
            "play_url": None,
            "poster_url": None,
            "material_name": material_name,
            "promotion_id": None if promotion_id is None else int(promotion_id),
            "promotion_name": promotion_name,
            "project_id": int(project_id),
            "project_name": project_name,
            "account_id": int(advertiser_id),
            "account_name": _display_name(str(account_name or ""), local_name),
            "stat_cost": _money(Decimal(cost)),
            "show_cnt": int(shows),
            "click_cnt": int(clicks),
            "ctr": _rate(Decimal(int(clicks)), Decimal(int(shows))),
            "cpc": _rate(Decimal(cost), Decimal(int(clicks))),
            "convert_cnt": int(converts),
            "convert_cost": _rate(Decimal(cost), Decimal(int(converts))),
            "convert_rate": _rate(Decimal(int(converts)) * 100, Decimal(int(clicks))),
        }
        for (
            material_id,
            video_id,
            material_name,
            promotion_id,
            promotion_name,
            project_id,
            project_name,
            advertiser_id,
            account_name,
            local_name,
            cost,
            shows,
            clicks,
            converts,
        ) in found
    ]
    rows.sort(key=lambda row: _sort_value(row, query.sort_by), reverse=query.sort_order == "desc")
    params = PageParams(page=query.page, page_size=query.page_size)
    page_rows = rows[params.offset : params.offset + params.page_size]
    await _fill_material_files(session, page_rows)
    return page_data(page_rows, len(rows), params)


async def _fill_material_files(session: AsyncSession, rows: list[dict[str, Any]]) -> None:
    """播放地址用素材库视频文件。第一帧没有单独存过，封面留空。"""
    video_ids = [int(row["video_id"]) for row in rows if row.get("video_id") is not None]
    if not video_ids:
        return
    videos = list(
        (
            await session.scalars(
                select(MaterialVideo).where(MaterialVideo.id.in_(video_ids), MaterialVideo.is_deleted == 0)
            )
        ).all()
    )
    by_id = {int(video.id): video for video in videos}
    for row in rows:
        video = None if row.get("video_id") is None else by_id.get(int(row["video_id"]))
        if video is None:
            continue
        urls = [str(url).strip() for url in (video.file_urls or []) if str(url).strip()]
        row["play_url"] = urls[0] if urls else None
        if video.name:
            row["material_name"] = video.name


async def _uni_faces(
    session: AsyncSession, found: list[tuple[OeProject, AdvertiserAccount, DeliverySubject]]
) -> dict[int, dict[str, str | None]]:
    """剧名来自短剧库，抖音号来自抖音号表，投手姓名是用户昵称。"""
    project_ids = [int(project.ocean_project_id) for project, _account, _subject in found]
    pitcher_ids = {
        int(account.pitcher_user_id) for _project, account, _subject in found if account.pitcher_user_id is not None
    }
    nicknames: dict[int, str] = {}
    if pitcher_ids:
        users = await session.execute(select(User.id, User.nickname).where(User.id.in_(pitcher_ids)))
        nicknames = {int(user_id): nickname for user_id, nickname in users.all()}
    series_names: dict[int, list[str | None]] = {}
    awemes: dict[int, list[str | None]] = {}
    douyin_names: dict[int, list[str | None]] = {}
    if project_ids:
        linked = await session.execute(
            select(
                OePromotion.ocean_project_id,
                ManhuaSeries.book_name,
                DouyinAccount.aweme_id,
                DouyinAccount.name,
            )
            .outerjoin(
                ManhuaSeries,
                and_(ManhuaSeries.id == OePromotion.series_id, ManhuaSeries.is_deleted == 0),
            )
            .outerjoin(
                DouyinAccount,
                and_(DouyinAccount.id == OePromotion.douyin_account_id, DouyinAccount.is_deleted == 0),
            )
            .where(OePromotion.ocean_project_id.in_(project_ids), OePromotion.is_deleted == 0)
        )
        for project_id, book_name, aweme_id, douyin_name in linked.all():
            if project_id is None:
                continue
            key = int(project_id)
            series_names.setdefault(key, []).append(book_name)
            awemes.setdefault(key, []).append(aweme_id)
            douyin_names.setdefault(key, []).append(douyin_name)
    fallback: list[tuple[int, str]] = []
    for project, _account, _subject in found:
        project_id = int(project.ocean_project_id)
        if _labels(awemes.get(project_id) or []) is None:
            aweme = _aweme_from_template(project.template)
            if aweme is not None:
                fallback.append((project_id, aweme))
    by_aweme: dict[str, str] = {}
    if fallback:
        rows = await session.execute(
            select(DouyinAccount.aweme_id, DouyinAccount.name).where(
                DouyinAccount.aweme_id.in_({aweme for _project_id, aweme in fallback}),
                DouyinAccount.delivery_mode == "uni",
                DouyinAccount.is_deleted == 0,
            )
        )
        by_aweme = {aweme_id: name for aweme_id, name in rows.all()}
    faces: dict[int, dict[str, str | None]] = {}
    for project, account, _subject in found:
        project_id = int(project.ocean_project_id)
        project_awemes = list(awemes.get(project_id) or [])
        project_names = list(douyin_names.get(project_id) or [])
        if _labels(project_awemes) is None:
            aweme = _aweme_from_template(project.template)
            if aweme is not None:
                project_awemes = [aweme]
                project_names = [by_aweme.get(aweme)]
        pitcher_name = None if account.pitcher_user_id is None else nicknames.get(int(account.pitcher_user_id))
        faces[project_id] = {
            "pitcher_name": pitcher_name,
            "series_name": _labels(series_names.get(project_id) or []),
            "douyin_aweme_id": _labels(project_awemes),
            "douyin_name": _labels(project_names),
        }
    return faces


async def list_uni_projects(
    session: AsyncSession, query: UniProjectQuery, principal: dict[str, Any]
) -> dict[str, Any]:
    """只列全域项目。创建结果先用创建当时的 message。创建成功的再查广告审核建议。"""
    if query.pitcher_user_id is not None:
        await _require_pitcher(session, query.pitcher_user_id)
    scope = await resolve_data_scope(session, principal)
    filters = [
        OeProject.is_deleted == 0,
        DeliverySubject.is_deleted == 0,
        DeliverySubject.delivery_mode == "uni",
        AdvertiserAccount.is_deleted == 0,
        owner_match(AdvertiserAccount.pitcher_user_id, int(principal["id"]), scope),
    ]
    if query.subject_id is not None:
        filters.append(DeliverySubject.id == query.subject_id)
    if query.project_id is not None:
        filters.append(OeProject.ocean_project_id == query.project_id)
    if query.series_id is not None:
        filters.append(_has_series(query.series_id))
    if query.account_id is not None:
        filters.append(OeProject.advertiser_id == query.account_id)
    if query.pitcher_user_id is not None:
        filters.append(AdvertiserAccount.pitcher_user_id == query.pitcher_user_id)
    if query.project_status is not None:
        filters.append(OeProject.opt_status == ("ENABLE" if query.project_status == "开启" else "DISABLE"))
    if query.douyin_account_id is not None:
        filters.append(
            select(OePromotion.id)
            .where(
                OePromotion.ocean_project_id == OeProject.ocean_project_id,
                OePromotion.douyin_account_id == query.douyin_account_id,
                OePromotion.is_deleted == 0,
            )
            .exists()
        )
    found = list(
        (
            await session.execute(
                select(OeProject, AdvertiserAccount, DeliverySubject)
                .join(DeliverySubject, OeProject.subject_id == DeliverySubject.id)
                .join(AdvertiserAccount, AdvertiserAccount.advertiser_id == OeProject.advertiser_id)
                .where(*filters)
            )
        ).all()
    )
    project_ids = [int(project.ocean_project_id) for project, _account, _subject in found]
    metrics = await _sum_by_project(session, project_ids, query.date_start, query.date_end)
    faces = await _uni_faces(session, found)
    rows = []
    for project, account, subject in found:
        metric = metrics.get(int(project.ocean_project_id))
        create_result, failure_reason = project_create_outcome(project.create_message)
        face = faces.get(int(project.ocean_project_id), {})
        rows.append(
            {
                "project_id": int(project.ocean_project_id),
                "project_name": project.name,
                "project_status": project_status_label(project.opt_status),
                "subject_name": subject.name,
                "account_id": int(account.advertiser_id),
                "account_name": _display_name(account.name, account.local_name),
                "pitcher_user_id": None if account.pitcher_user_id is None else int(account.pitcher_user_id),
                "pitcher_name": face.get("pitcher_name"),
                "series_name": face.get("series_name"),
                "douyin_aweme_id": face.get("douyin_aweme_id"),
                "douyin_name": face.get("douyin_name"),
                "stat_cost": _money(_seven(metric)[0]),
                "budget": _budget(project.template),
                "roi_goal": _stored_roi(project.template),
                "created_at": project.created_date.isoformat(),
                "create_result": create_result,
                "failure_reason": failure_reason,
            }
        )
    rows.sort(key=lambda row: _sort_value(row, query.sort_by), reverse=query.sort_order == "desc")
    params = PageParams(page=query.page, page_size=query.page_size)
    page_rows = rows[params.offset : params.offset + params.page_size]
    page_projects = {
        int(project.ocean_project_id): project
        for project, _account, _subject in found
        if int(project.ocean_project_id) in {int(row["project_id"]) for row in page_rows}
    }
    await _fill_roi(session, page_rows, page_projects)
    await _fill_uni_failure_reasons(session, page_rows)
    return page_data(page_rows, len(rows), params)


def _as_filled(value: Any) -> str | None:
    """创建页填多少就显示多少，不改位数。"""
    try:
        text = format(Decimal(str(value)), "f")
    except InvalidOperation:
        return None
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _stored_roi(template: dict | None) -> str:
    """创建时写入的 ROI 系数。没填过是 -。"""
    if not isinstance(template, dict):
        return "-"
    setting = template.get("delivery_setting")
    if not isinstance(setting, dict) or setting.get("roi_goal") is None:
        return "-"
    return _as_filled(setting.get("roi_goal")) or "-"


def roi_text(item: dict[str, Any]) -> str | None:
    """项目列表 delivery_setting.roi_goal。没有或不是数则不更新。"""
    setting = item.get("delivery_setting")
    if not isinstance(setting, dict) or setting.get("roi_goal") is None:
        return None
    return _as_filled(setting.get("roi_goal"))


def project_create_outcome(create_message: str | None) -> tuple[str, str | None]:
    """创建当时的结果。有巨量返回的 message 就是创建失败。"""
    if create_message:
        return "创建失败", create_message
    return "创建成功", None


def apply_reject_reasons(
    rows: list[dict[str, Any]], found: dict[int, list[str]], failed: set[int]
) -> None:
    """查到原因就用原因。这一批接口失败是 -。查到了但没有原因才是空数组。"""
    for row in rows:
        item_id = int(row["promotion_id"])
        if item_id in found:
            row["reject_reasons"] = found[item_id]
        elif item_id in failed:
            row["reject_reasons"] = ["-"]
        else:
            row["reject_reasons"] = []


def reject_lines(item: dict[str, Any]) -> list[str]:
    """广告审核建议和素材审核建议里的拒绝原因，去重并保持出现顺序。"""
    found: list[str] = []
    for key in ("promotion_reject", "material_reject"):
        for block in item.get(key) or []:
            if not isinstance(block, dict):
                continue
            for text in block.get("reject_reason") or []:
                line = str(text).strip()
                if line and line not in found:
                    found.append(line)
    return found


def stored_budget_mode(template: dict | None) -> str:
    """创建时记下的预算类型。没有就用设置预算对应的日预算档。"""
    setting = template.get("delivery_setting") if isinstance(template, dict) else None
    mode = setting.get("budget_mode") if isinstance(setting, dict) else None
    if isinstance(mode, str) and mode.strip():
        return mode
    return "BUDGET_MODE_DAY"


def _write_budget(project: OeProject, amount: Decimal) -> None:
    """只改目标预算金额，不改预算类型。"""
    template = dict(project.template or {})
    setting = dict(template.get("delivery_setting") or {})
    setting["budget"] = float(amount)
    template["delivery_setting"] = setting
    project.template = template


async def update_project_budgets(
    session: AsyncSession, body: ProjectBudgetWrite, principal: dict[str, Any]
) -> dict[str, Any]:
    """批量改项目目标预算。只改当前登录人能看的项目，并通知巨量。"""
    projects = await _visible_projects(session, body.project_ids, principal)
    accepted, messages = await _push_grouped_budget(session, projects, body.budget)
    for project in projects:
        if int(project.ocean_project_id) in accepted:
            _write_budget(project, body.budget)
    await session.flush()
    if messages:
        await session.commit()
        raise ApiError(502, "；".join(messages))
    return {"project_ids": sorted(accepted)}


async def batch_promotions(
    session: AsyncSession, body: PromotionBatchWrite, principal: dict[str, Any]
) -> dict[str, Any]:
    """批量开启、暂停或删除广告。删除先通知巨量，接受的才在本库软删。不改所属项目。"""
    scope = await resolve_data_scope(session, principal)
    promotions = list(
        (
            await session.scalars(
                select(OePromotion)
                .join(AdvertiserAccount, AdvertiserAccount.advertiser_id == OePromotion.advertiser_id)
                .where(
                    OePromotion.promotion_id.in_(body.promotion_ids),
                    OePromotion.is_deleted == 0,
                    AdvertiserAccount.is_deleted == 0,
                    owner_match(AdvertiserAccount.pitcher_user_id, int(principal["id"]), scope),
                )
            )
        ).all()
    )
    status = batch_status(body.action)
    if status is None:
        accepted, messages = await _push_grouped_delete(
            session,
            _ids_by_advertiser([(int(row.advertiser_id), int(row.promotion_id)) for row in promotions]),
            id_key="promotion_id",
            kind="promotion",
        )
        for promotion in promotions:
            if int(promotion.promotion_id) in accepted:
                promotion.mark_deleted()
        await session.flush()
        if messages:
            await session.commit()
            raise ApiError(502, "；".join(messages))
        return {"promotion_ids": sorted(accepted)}
    accepted, messages = await _push_grouped_status(
        session,
        _ids_by_advertiser([(int(row.advertiser_id), int(row.promotion_id)) for row in promotions]),
        status,
        id_key="promotion_id",
        kind="promotion",
    )
    for promotion in promotions:
        if int(promotion.promotion_id) in accepted:
            promotion.opt_status = status
    await session.flush()
    if messages:
        await session.commit()
        raise ApiError(502, "；".join(messages))
    return {"promotion_ids": sorted(accepted)}


async def _visible_projects(
    session: AsyncSession, project_ids: list[int], principal: dict[str, Any]
) -> list[OeProject]:
    scope = await resolve_data_scope(session, principal)
    return list(
        (
            await session.scalars(
                select(OeProject)
                .join(AdvertiserAccount, AdvertiserAccount.advertiser_id == OeProject.advertiser_id)
                .where(
                    OeProject.ocean_project_id.in_(project_ids),
                    OeProject.is_deleted == 0,
                    AdvertiserAccount.is_deleted == 0,
                    owner_match(AdvertiserAccount.pitcher_user_id, int(principal["id"]), scope),
                )
            )
        )
        .unique()
        .all()
    )


async def _push_grouped_budget(
    session: AsyncSession, projects: list[OeProject], amount: Decimal
) -> tuple[set[int], list[str]]:
    """按账户调用巨量项目预算更新。金额用新的目标预算，类型用项目上已有的。一次最多 10 条。"""
    grouped: dict[int, list[tuple[int, str]]] = {}
    for project in projects:
        grouped.setdefault(int(project.advertiser_id), []).append(
            (int(project.ocean_project_id), stored_budget_mode(project.template))
        )
    if not grouped:
        return set(), []
    client = get_ocean_client()
    token = await _access_token(session)
    accepted: set[int] = set()
    messages: list[str] = []
    for advertiser_id, items in grouped.items():
        for start in range(0, len(items), _OCEAN_STATUS_BATCH):
            chunk = items[start : start + _OCEAN_STATUS_BATCH]
            body = {
                "advertiser_id": advertiser_id,
                "data": [
                    {
                        "project_id": project_id,
                        "budget_mode": mode,
                        "budget": float(amount),
                    }
                    for project_id, mode in chunk
                ],
            }
            try:
                remote = await client.update_project_budget(token, body)
            except OceanEngineError as exc:
                messages.append(str(exc))
                continue
            ok, failed = accepted_status_ids(remote, "project_ids", [project_id for project_id, _mode in chunk])
            accepted.update(ok)
            messages.extend(failed)
    return accepted, messages


async def _fill_reject_reasons(session: AsyncSession, rows: list[dict[str, Any]]) -> None:
    """当前页按账户向巨量要审核失败原因。这一批查失败时原因是 -。"""
    if not rows:
        return
    failed = {int(row["promotion_id"]) for row in rows}
    try:
        client = get_ocean_client()
        token = await _access_token(session)
    except (ApiError, OceanEngineError):
        apply_reject_reasons(rows, {}, failed)
        return
    grouped: dict[int, list[int]] = {}
    for row in rows:
        grouped.setdefault(int(row["account_id"]), []).append(int(row["promotion_id"]))
    found: dict[int, list[str]] = {}
    failed: set[int] = set()
    for advertiser_id, promotion_ids in grouped.items():
        for start in range(0, len(promotion_ids), _OCEAN_STATUS_BATCH):
            chunk = promotion_ids[start : start + _OCEAN_STATUS_BATCH]
            try:
                remote = await client.list_promotion_reject_reasons(token, advertiser_id, chunk)
            except OceanEngineError:
                failed.update(chunk)
                continue
            data = remote.get("data") if isinstance(remote, dict) else None
            for item in (data or {}).get("list") or []:
                if isinstance(item, dict) and item.get("promotion_id") is not None:
                    found[int(item["promotion_id"])] = reject_lines(item)
    apply_reject_reasons(rows, found, failed)


async def _fill_uni_failure_reasons(session: AsyncSession, rows: list[dict[str, Any]]) -> None:
    """创建成功的项目，用下面广告的审核建议补失败原因。创建当时的 message 不再改。"""
    pending = [row for row in rows if row.get("create_result") == "创建成功"]
    if not pending:
        return
    project_ids = [int(row["project_id"]) for row in pending]
    promotions = list(
        (
            await session.execute(
                select(OePromotion.ocean_project_id, OePromotion.promotion_id, OePromotion.advertiser_id).where(
                    OePromotion.ocean_project_id.in_(project_ids),
                    OePromotion.is_deleted == 0,
                )
            )
        ).all()
    )
    by_project: dict[int, list[tuple[int, int]]] = {}
    for ocean_project_id, promotion_id, advertiser_id in promotions:
        if ocean_project_id is None or promotion_id is None:
            continue
        by_project.setdefault(int(ocean_project_id), []).append((int(advertiser_id), int(promotion_id)))
    if not by_project:
        return
    promo_project: dict[int, int] = {}
    grouped: dict[int, list[int]] = {}
    for project_id, pairs in by_project.items():
        for advertiser_id, promotion_id in pairs:
            grouped.setdefault(advertiser_id, []).append(promotion_id)
            promo_project[promotion_id] = project_id
    reasons: dict[int, list[str]] = {}
    failed: set[int] = set()
    try:
        client = get_ocean_client()
        token = await _access_token(session)
    except (ApiError, OceanEngineError):
        failed.update(by_project)
    else:
        for advertiser_id, promotion_ids in grouped.items():
            for start in range(0, len(promotion_ids), _OCEAN_STATUS_BATCH):
                chunk = promotion_ids[start : start + _OCEAN_STATUS_BATCH]
                try:
                    remote = await client.list_promotion_reject_reasons(token, advertiser_id, chunk)
                except OceanEngineError:
                    failed.update(promo_project[promotion_id] for promotion_id in chunk)
                    continue
                data = remote.get("data") if isinstance(remote, dict) else None
                for item in (data or {}).get("list") or []:
                    if not isinstance(item, dict) or item.get("promotion_id") is None:
                        continue
                    project_id = promo_project.get(int(item["promotion_id"]))
                    if project_id is None:
                        continue
                    bucket = reasons.setdefault(project_id, [])
                    for line in reject_lines(item):
                        if line not in bucket:
                            bucket.append(line)
    for row in pending:
        project_id = int(row["project_id"])
        lines = reasons.get(project_id) or []
        if lines:
            row["failure_reason"] = "；".join(lines)
        elif project_id in failed:
            row["failure_reason"] = "-"


def _write_roi(project: OeProject, amount: str) -> None:
    """把巨量返回的当前 ROI 系数写回创建时存下的那一格。"""
    template = dict(project.template or {})
    setting = dict(template.get("delivery_setting") or {})
    setting["roi_goal"] = float(amount)
    template["delivery_setting"] = setting
    project.template = template


async def _fill_roi(
    session: AsyncSession,
    rows: list[dict[str, Any]],
    projects: dict[int, OeProject],
) -> None:
    """先显示创建时填的系数。向巨量查到新的 roi_goal 再更新这一格。查失败或不返回则保留原数。"""
    if not rows:
        return
    try:
        client = get_ocean_client()
        token = await _access_token(session)
    except (ApiError, OceanEngineError):
        return
    grouped: dict[int, list[int]] = {}
    for row in rows:
        grouped.setdefault(int(row["account_id"]), []).append(int(row["project_id"]))
    for advertiser_id, project_ids in grouped.items():
        for start in range(0, len(project_ids), _OCEAN_STATUS_BATCH):
            chunk = project_ids[start : start + _OCEAN_STATUS_BATCH]
            try:
                remote = await client.list_projects(
                    token,
                    {
                        "advertiser_id": advertiser_id,
                        "filtering": json.dumps({"ids": chunk}),
                        "page": 1,
                        "page_size": len(chunk),
                    },
                )
            except OceanEngineError:
                continue
            data = remote.get("data") if isinstance(remote, dict) else None
            for item in (data or {}).get("list") or []:
                if not isinstance(item, dict) or item.get("project_id") is None:
                    continue
                text = roi_text(item)
                if text is None:
                    continue
                project_id = int(item["project_id"])
                project = projects.get(project_id)
                if project is not None:
                    _write_roi(project, text)
                for row in rows:
                    if int(row["project_id"]) == project_id:
                        row["roi_goal"] = text
    await session.flush()
