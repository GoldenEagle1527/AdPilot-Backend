"""授权组织和广告主名单。只读库。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.pagination import PageParams, page_data
from app.core.times import beijing_now
from app.modules.account.model import AdvertiserAccount, OeApp, OeOrganization, OeOrganizationGrant, OeToken
from app.modules.oceanengine.schema import AdvertiserQuery
from app.modules.system_admin.domain.models import User
from app.modules.system_admin.domain.scope import DataScope, owner_match


def _configured_ocean_app_id() -> int | None:
    """关闭 mock 且配置了数字 app_id 时，广告主列表只看这个应用。"""
    settings = get_settings().oceanengine
    if settings.mock:
        return None
    text = settings.app_id.strip()
    if text.isdigit():
        return int(text)
    return None


def organization_token_valid(
    *,
    access_token: str | None,
    last_error: str | None,
    access_expire_at: datetime | None,
    now: datetime,
) -> bool:
    """有访问令牌、没有刷新失败，且未过期。"""
    if not access_token or (last_error or "").strip():
        return False
    if access_expire_at is not None and access_expire_at <= now:
        return False
    return True


async def list_organizations(session: AsyncSession, params: PageParams) -> dict[str, Any]:
    """授权组织分页。只读表。自研和三方都返回，不按配置的应用过滤。"""
    now = beijing_now()
    joined = (
        select(
            OeOrganizationGrant.id,
            OeOrganization.ocean_account_id,
            OeOrganization.name,
            OeOrganization.account_role,
            OeOrganization.ocean_version,
            OeOrganizationGrant.status,
            OeApp.channel,
            OeToken.access_token,
            OeToken.last_error,
            OeToken.access_expire_at,
        )
        .join(OeOrganization, OeOrganizationGrant.organization_id == OeOrganization.id)
        .join(OeApp, OeOrganizationGrant.oe_app_id == OeApp.id)
        .outerjoin(
            OeToken,
            (OeToken.oe_app_id == OeApp.id) & (OeToken.is_deleted == 0),
        )
        .where(
            OeOrganizationGrant.is_deleted == 0,
            OeOrganization.is_deleted == 0,
            OeApp.is_deleted == 0,
        )
    )
    total = int(await session.scalar(select(func.count()).select_from(joined.subquery())) or 0)
    rows = await session.execute(
        joined.order_by(OeOrganizationGrant.id).offset(params.offset).limit(params.page_size)
    )
    items = [
        {
            "id": int(row_id),
            "advertiser_id": int(ocean_account_id),
            "advertiser_name": name,
            "account_role": account_role,
            "ocean_version": ocean_version,
            "channel": channel,
            "status": status,
            "token_valid": organization_token_valid(
                access_token=access_token,
                last_error=last_error,
                access_expire_at=access_expire_at,
                now=now,
            ),
        }
        for (
            row_id,
            ocean_account_id,
            name,
            account_role,
            ocean_version,
            status,
            channel,
            access_token,
            last_error,
            access_expire_at,
        ) in rows.all()
    ]
    return page_data(items, total, params)


def org_wide_owner(scope: DataScope):
    """菜单 63 的广告主：仅本人看自己的户；勾了部门则看这些部门投手的户，以及未分配的户。"""
    if scope.self_only:
        return AdvertiserAccount.pitcher_user_id == scope.user_id
    return or_(
        owner_match(AdvertiserAccount.pitcher_user_id, scope.user_id, scope),
        AdvertiserAccount.pitcher_user_id.is_(None),
    )


async def list_advertisers(
    session: AsyncSession,
    query: AdvertiserQuery,
    scope: DataScope | None = None,
    *,
    org_wide: bool = False,
) -> dict[str, Any]:
    """广告主分页。只读表。org_wide 时按数据范围收窄，不再返回全部户。"""
    params = PageParams(page=query.page, page_size=query.page_size)
    filters = [AdvertiserAccount.is_deleted == 0, OeOrganization.is_deleted == 0]
    app_id = _configured_ocean_app_id()
    if app_id is not None:
        filters.append(OeApp.app_id == app_id)
        filters.append(OeApp.is_deleted == 0)
    if query.account_id is not None:
        filters.append(AdvertiserAccount.advertiser_id == query.account_id)
    if query.organization_id is not None:
        filters.append(OeOrganization.ocean_account_id == query.organization_id)
    if org_wide and scope is not None:
        filters.append(org_wide_owner(scope))
    elif query.only_user_id is not None:
        filters.append(AdvertiserAccount.pitcher_user_id == query.only_user_id)
        filters.append(AdvertiserAccount.sync_status == "active")
    elif query.pitcher_user_id is not None:
        filters.append(AdvertiserAccount.pitcher_user_id == query.pitcher_user_id)
    name = (query.account_name or "").strip()
    if name:
        pattern = _like(name)
        filters.append(
            or_(
                AdvertiserAccount.name.ilike(pattern, escape="\\"),
                AdvertiserAccount.local_name.ilike(pattern, escape="\\"),
            )
        )
    joined = (
        select(
            AdvertiserAccount.advertiser_id,
            AdvertiserAccount.name,
            AdvertiserAccount.local_name,
            AdvertiserAccount.valid_balance,
            AdvertiserAccount.company_name,
            AdvertiserAccount.sync_status,
            OeOrganization.ocean_account_id,
            OeOrganization.name.label("manager_name"),
            User.nickname,
        )
        .join(OeOrganization, AdvertiserAccount.organization_id == OeOrganization.id)
        .join(OeApp, AdvertiserAccount.oe_app_id == OeApp.id)
        .outerjoin(
            User,
            (AdvertiserAccount.pitcher_user_id == User.id) & (User.is_deleted == 0),
        )
        .where(*filters)
    )
    total = int(await session.scalar(select(func.count()).select_from(joined.subquery())) or 0)
    page_rows = await session.execute(
        joined.order_by(AdvertiserAccount.id).offset(params.offset).limit(params.page_size)
    )
    items = [_advertiser_item(row) for row in page_rows.all()]
    return page_data(items, total, params)


def _advertiser_item(row: Any) -> dict[str, Any]:
    local_name = str(row.local_name or "").strip()
    balance = row.valid_balance
    return {
        "account_id": int(row.advertiser_id),
        "account_name": local_name or str(row.name or ""),
        "valid_balance": float(balance if balance is not None else 0),
        "adv_company_name": str(row.company_name or ""),
        "organization_id": int(row.ocean_account_id),
        "pitcher_nickname": str(row.nickname or ""),
        "manager_name": str(row.manager_name or ""),
        "sync_status": str(row.sync_status or "active"),
    }


def _like(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
