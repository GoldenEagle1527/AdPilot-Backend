"""从开放平台拉取授权组织和广告主，并补余额与公司名。"""

from __future__ import annotations

import asyncio
import csv
import io
from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.times import beijing_now
from app.modules.account.model import AdvertiserAccount, OeApp, OeOrganization, OeOrganizationGrant
from app.modules.oceanengine.client import OceanEngineError, OceanEnginePort
from app.modules.oceanengine.runtime import (
    _PAGE_SIZE,
    _access_token,
    _app_for_live,
    _page_count,
    get_ocean_client,
)

_EBP_ROLES = frozenset(
    {
        "PLATFORM_ROLE_ENTERPRISE_BP_ADMIN",
        "PLATFORM_ROLE_ENTERPRISE_BP_OPERATOR",
    }
)
_CUSTOMER_ADMIN = "CUSTOMER_ADMIN"
_ORG_ROLES = _EBP_ROLES | {_CUSTOMER_ADMIN}
_LIST_CAP = 10_000
_BALANCE_BATCH = 200
_BALANCE_TTL = timedelta(days=1)
_TASK_POLLS = 3
_EBP_ROLE_PREFIX = "PLATFORM_ROLE_ENTERPRISE_BP_"
_LEGACY_WORKBENCH_ROLES = frozenset({"CUSTOMER_ADMIN", "CUSTOMER_OPERATOR"})


def ocean_version_for_role(account_role: str) -> str:
    """接口没有版本字段。升级版工作台和旧版工作台由 account_type 区分。"""
    role = account_role.strip()
    if role.startswith(_EBP_ROLE_PREFIX):
        return "升级版组织"
    if role in _LEGACY_WORKBENCH_ROLES:
        return "旧版工作台"
    return role


async def sync_from_oceanengine(session: AsyncSession, app: OeApp | None = None) -> None:
    """手动同步或回调之后调用。先组织，再广告主。传入的应用优先于配置里的应用。"""
    target = app or await _app_for_live(session)
    await _sync_organizations(session, target)
    await _sync_advertisers(session, target)


async def _sync_organizations(session: AsyncSession, app: OeApp) -> OeApp:
    client = get_ocean_client()
    body = await client.list_authorized_accounts(await _access_token(session, app))
    rows = (body.get("data") or {}).get("list") or []
    seen: list[int] = []
    for raw in rows:
        if not isinstance(raw, dict) or raw.get("is_valid") is False:
            continue
        identity = _organization_identity(raw)
        if identity is None:
            continue
        ocean_account_id, name, role = identity
        seen.append(ocean_account_id)
        found = await session.scalar(
            select(OeOrganization)
            .where(OeOrganization.ocean_account_id == ocean_account_id)
            .order_by(OeOrganization.is_deleted, OeOrganization.id)
            .limit(1)
        )
        version = ocean_version_for_role(role)
        if found is None:
            found = OeOrganization(
                ocean_account_id=ocean_account_id,
                name=name,
                account_role=role,
                ocean_version=version,
                status="active",
                raw_payload=raw,
            )
            session.add(found)
            await session.flush()
        else:
            found.name = name or found.name
            found.account_role = role or found.account_role
            if version:
                found.ocean_version = version
            found.status = "active"
            found.is_deleted = 0
            found.deleted_at = None
            found.raw_payload = raw
        await _upsert_grant(session, found, app)
    await session.flush()
    await _invalidate_missing_grants(session, app, seen)
    await _refresh_organization_status(session)
    await session.flush()
    return app


async def _sync_advertisers(session: AsyncSession, app: OeApp) -> None:
    client = get_ocean_client()
    token = await _access_token(session, app)
    orgs = (
        await session.scalars(
            select(OeOrganization)
            .join(OeOrganizationGrant, OeOrganizationGrant.organization_id == OeOrganization.id)
            .where(
                OeOrganizationGrant.oe_app_id == app.id,
                OeOrganizationGrant.status == "active",
                OeOrganizationGrant.is_deleted == 0,
                OeOrganization.is_deleted == 0,
                OeOrganization.account_role.in_(_ORG_ROLES),
            )
        )
    ).all()
    for org in orgs:
        accounts, complete = await _list_org_advertisers(client, token, session, org)
        for account in accounts:
            await _upsert_advertiser_name(
                session,
                app=app,
                org=org,
                account_id=int(account["account_id"]),
                account_name=str(account.get("account_name") or ""),
                raw_payload={"account": account},
            )
        if complete:
            seen = [int(account["account_id"]) for account in accounts]
            stale = update(AdvertiserAccount).where(
                AdvertiserAccount.organization_id == org.id,
                AdvertiserAccount.is_deleted == 0,
            )
            if seen:
                stale = stale.where(AdvertiserAccount.advertiser_id.not_in(seen))
            await session.execute(stale.values(sync_status="missing"))
        await _refresh_balance_batch(session, client, token, org)
    await session.flush()


async def _upsert_advertiser(
    session: AsyncSession,
    *,
    app: OeApp,
    org: OeOrganization,
    account_id: int,
    account_name: str,
    balance: Decimal,
    company_name: str,
    raw_payload: dict[str, Any],
) -> None:
    found = await session.scalar(
        select(AdvertiserAccount)
        .where(AdvertiserAccount.advertiser_id == account_id)
        .order_by(
            AdvertiserAccount.unbound_at.is_not(None).desc(),
            AdvertiserAccount.is_deleted,
            AdvertiserAccount.id,
        )
        .limit(1)
    )
    if _is_unbound(found):
        return
    now = beijing_now()
    if found is None:
        session.add(
            AdvertiserAccount(
                organization_id=org.id,
                oe_app_id=app.id,
                advertiser_id=account_id,
                name=account_name,
                valid_balance=balance,
                company_name=company_name,
                balance_synced_at=now,
                company_synced_at=now,
                sync_status="active",
                raw_payload=raw_payload,
            )
        )
        return
    found.organization_id = org.id
    found.oe_app_id = app.id
    found.name = account_name or found.name
    found.valid_balance = balance
    found.company_name = company_name
    found.balance_synced_at = now
    found.company_synced_at = now
    found.sync_status = "active"
    found.is_deleted = 0
    found.deleted_at = None
    found.raw_payload = raw_payload


def _balance_amount(data: dict[str, Any]) -> Decimal:
    """开放平台可能给 account_valid 或 valid_balance，都写入 valid_balance。"""
    raw = data.get("account_valid")
    if raw is None:
        raw = data.get("valid_balance")
    if raw is None:
        return Decimal("0.00")
    return Decimal(str(raw)).quantize(Decimal("0.01"))


def _company_name(body: dict[str, Any], account_id: int) -> str:
    """公开信息的公司名在 data[].company，或包在 data.advertisers 里。"""
    data = body.get("data")
    if isinstance(data, list):
        details = data
    elif isinstance(data, dict):
        details = data.get("advertisers") or []
    else:
        details = []
    for item in details:
        if not isinstance(item, dict):
            continue
        if int(item.get("id") or item.get("advertiser_id") or 0) == account_id:
            return str(item.get("company") or item.get("adv_company_name") or "")
    return ""


def _is_unbound(row: AdvertiserAccount | None) -> bool:
    """解绑行留在库里，同步不能把它加回列表，也不能另插一条未删除行。"""
    return row is not None and row.unbound_at is not None


async def _upsert_grant(session: AsyncSession, org: OeOrganization, app: OeApp) -> None:
    grant = await session.scalar(
        select(OeOrganizationGrant).where(
            OeOrganizationGrant.organization_id == org.id,
            OeOrganizationGrant.oe_app_id == app.id,
        )
    )
    if grant is None:
        session.add(OeOrganizationGrant(organization_id=org.id, oe_app_id=app.id, status="active"))
        return
    grant.status = "active"
    grant.is_deleted = 0
    grant.deleted_at = None


async def _invalidate_missing_grants(session: AsyncSession, app: OeApp, seen: list[int]) -> None:
    """这次没返回的账户，只让当前应用的授权失效。"""
    org_ids = select(OeOrganization.id).where(OeOrganization.is_deleted == 0)
    if seen:
        org_ids = org_ids.where(OeOrganization.ocean_account_id.not_in(seen))
    await session.execute(
        update(OeOrganizationGrant)
        .where(
            OeOrganizationGrant.oe_app_id == app.id,
            OeOrganizationGrant.is_deleted == 0,
            OeOrganizationGrant.organization_id.in_(org_ids),
        )
        .values(status="invalid")
    )


async def _refresh_organization_status(session: AsyncSession) -> None:
    """还有任一有效授权则组织有效；全部失效才标 invalid。"""
    active_ids = select(OeOrganizationGrant.organization_id).where(
        OeOrganizationGrant.status == "active",
        OeOrganizationGrant.is_deleted == 0,
    )
    await session.execute(
        update(OeOrganization)
        .where(OeOrganization.is_deleted == 0, OeOrganization.id.in_(active_ids))
        .values(status="active")
    )
    await session.execute(
        update(OeOrganization)
        .where(OeOrganization.is_deleted == 0, OeOrganization.id.not_in(active_ids))
        .values(status="invalid")
    )


def _organization_identity(raw: dict[str, Any]) -> tuple[int, str, str] | None:
    """优先现行字段 account_id / account_name / account_type。"""
    account_id = raw.get("account_id")
    if account_id is None:
        account_id = raw.get("advertiser_id")
    if account_id is None:
        return None
    name = str(raw.get("account_name") or raw.get("advertiser_name") or "")
    role = str(raw.get("account_type") or raw.get("account_role") or "")
    return int(account_id), name, role


def _account_row(raw: dict[str, Any]) -> dict[str, Any] | None:
    account_id = raw.get("account_id")
    if account_id is None:
        account_id = raw.get("advertiser_id")
    if account_id is None:
        return None
    name = raw.get("account_name")
    if not name:
        name = raw.get("advertiser_name") or ""
    return {"account_id": int(account_id), "account_name": str(name)}


def list_exceeds_cap(data: dict[str, Any], page_size: int) -> bool:
    """名单超过开放平台实时接口的 1 万条上限。"""
    page_info = data.get("page_info") or {}
    total = page_info.get("total_number")
    if total is not None:
        return int(total) > _LIST_CAP
    pages = page_info.get("total_page")
    if pages is not None:
        return int(pages) * page_size > _LIST_CAP
    return False


def accounts_from_download(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """把导出结果收成 account_id / account_name。"""
    data = payload.get("data")
    rows: list[Any] = []
    if isinstance(data, dict):
        nested = data.get("account_list") or data.get("list") or []
        if isinstance(nested, list):
            rows = nested
    elif isinstance(data, list):
        rows = data
    text = payload.get("raw_text")
    if not rows and isinstance(text, str) and text.strip():
        rows = _csv_account_rows(text)
    found: list[dict[str, Any]] = []
    for raw in rows:
        if isinstance(raw, dict):
            row = _account_row(raw)
            if row is not None:
                found.append(row)
    return found


def _csv_account_rows(text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(text))
    return [dict(item) for item in reader]


async def _list_org_advertisers(
    client: OceanEnginePort, token: str, session: AsyncSession, org: OeOrganization
) -> tuple[list[dict[str, Any]], bool]:
    """返回广告主名单，以及这份名单是否完整。"""
    org_id = int(org.ocean_account_id)
    if org.account_role == _CUSTOMER_ADMIN:
        return await _collect_capped(
            lambda page: client.list_customer_center_advertisers(
                token, org_id, page=page, page_size=_PAGE_SIZE
            )
        )
    first = await client.list_ebp_advertisers(token, org_id, page=1, page_size=_PAGE_SIZE)
    data = first.get("data") or {}
    if list_exceeds_cap(data, _PAGE_SIZE):
        return await _ebp_account_export(client, token, session, org)
    return await _collect_capped(
        lambda page: client.list_ebp_advertisers(token, org_id, page=page, page_size=_PAGE_SIZE)
    )


async def _collect_capped(fetch: Any) -> tuple[list[dict[str, Any]], bool]:
    """按页收集，不超过 1 万条。超过则名单不完整。"""
    page = 1
    found: list[dict[str, Any]] = []
    complete = True
    while page < 10_000 and len(found) < _LIST_CAP:
        body = await fetch(page)
        data = body.get("data") or {}
        if list_exceeds_cap(data, _PAGE_SIZE):
            complete = False
        batch = data.get("account_list") or data.get("list") or []
        if not isinstance(batch, list):
            break
        for raw in batch:
            if isinstance(raw, dict):
                row = _account_row(raw)
                if row is not None:
                    found.append(row)
        if len(found) >= _LIST_CAP and page < _page_count(data, len(batch)):
            complete = False
            break
        if page >= _page_count(data, len(batch)):
            break
        page += 1
    return found[:_LIST_CAP], complete


async def _ebp_account_export(
    client: OceanEnginePort, token: str, session: AsyncSession, org: OeOrganization
) -> tuple[list[dict[str, Any]], bool]:
    """超过 1 万条时创建或接着查异步导出。未完成则名单不完整。"""
    task_id = org.ebp_account_task_id
    status = org.ebp_account_task_status or ""
    if task_id is None or status in {"FAILED", "EXPIRED"}:
        created = await client.create_ebp_advertiser_task(token, int(org.ocean_account_id))
        task_id = int((created.get("data") or {}).get("task_id") or 0) or None
        org.ebp_account_task_id = task_id
        org.ebp_account_task_status = "EXECUTING"
        await session.commit()
    if task_id is None:
        return [], False
    for attempt in range(_TASK_POLLS):
        listed = await client.list_ebp_advertiser_tasks(
            token, int(org.ocean_account_id), [int(task_id)]
        )
        items = (listed.get("data") or {}).get("list") or []
        current = items[0] if items and isinstance(items[0], dict) else {}
        status = str(current.get("task_status") or "EXECUTING")
        org.ebp_account_task_status = status
        if status == "COMPLETED":
            payload = await client.download_ebp_advertiser_task(
                token, int(org.ocean_account_id), int(task_id)
            )
            rows = accounts_from_download(payload)
            await session.flush()
            if not rows:
                return [], False
            return rows, True
        if status in {"FAILED", "EXPIRED"}:
            await session.flush()
            return [], False
        if attempt + 1 < _TASK_POLLS:
            await asyncio.sleep(2)
    await session.flush()
    return [], False


async def _upsert_advertiser_name(
    session: AsyncSession,
    *,
    app: OeApp,
    org: OeOrganization,
    account_id: int,
    account_name: str,
    raw_payload: dict[str, Any],
) -> None:
    """只写名单。余额和公司名留给按批补齐。"""
    found = await session.scalar(
        select(AdvertiserAccount)
        .where(AdvertiserAccount.advertiser_id == account_id)
        .order_by(
            AdvertiserAccount.unbound_at.is_not(None).desc(),
            AdvertiserAccount.is_deleted,
            AdvertiserAccount.id,
        )
        .limit(1)
    )
    if _is_unbound(found):
        return
    if found is None:
        session.add(
            AdvertiserAccount(
                organization_id=org.id,
                oe_app_id=app.id,
                advertiser_id=account_id,
                name=account_name,
                sync_status="active",
                raw_payload=raw_payload,
            )
        )
        return
    found.organization_id = org.id
    found.oe_app_id = app.id
    found.name = account_name or found.name
    found.sync_status = "active"
    found.is_deleted = 0
    found.deleted_at = None
    found.raw_payload = raw_payload


async def _refresh_balance_batch(
    session: AsyncSession, client: OceanEnginePort, token: str, org: OeOrganization
) -> None:
    """给过期或未同步的户补余额和公司名。单户失败不影响名单。"""
    cutoff = beijing_now() - _BALANCE_TTL
    rows = (
        await session.scalars(
            select(AdvertiserAccount)
            .where(
                AdvertiserAccount.organization_id == org.id,
                AdvertiserAccount.is_deleted == 0,
                or_(
                    AdvertiserAccount.balance_synced_at.is_(None),
                    AdvertiserAccount.balance_synced_at < cutoff,
                ),
            )
            .order_by(AdvertiserAccount.id)
            .limit(_BALANCE_BATCH)
        )
    ).all()
    now = beijing_now()
    for row in rows:
        try:
            fund = await client.fund_get(token, int(row.advertiser_id))
            info = await client.advertiser_public_info(token, [int(row.advertiser_id)])
        except OceanEngineError:
            continue
        fund_data = fund.get("data") or {}
        row.valid_balance = _balance_amount(fund_data)
        row.company_name = _company_name(info, int(row.advertiser_id))
        row.balance_synced_at = now
        row.company_synced_at = now
