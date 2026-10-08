"""巨量夹具对应的落库种子。启动在 mock 时调用一次，import 不写库。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.times import beijing_now
from app.modules.account.model import (
    AdvertiserAccount,
    OeApp,
    OeOrganization,
    OeOrganizationGrant,
    OeReportSnapshot,
)

# 配置键名，不是密钥明文。
_SELF_SECRET_KEY = "oceanengine.self.secret"
_THIRD_SECRET_KEY = "oceanengine.third.secret"

_COMPANY_NAME = "番茄漫剧~普通-我花-我家-低调-岁月-苏子-我替-我不-萌宝-重生-杭州瑶添IAA-常规-48-king-免费#2"

_SELF_APP_ID = 1870855836080240
_THIRD_APP_ID = 1870857293665690
_ORG_OCEAN_ID = 1872115109920903
_ADVERTISER_ID = 1873916032590219


async def ensure_oceanengine_seed(session: AsyncSession) -> None:
    """幂等插入两套应用、一条共享组织、两条授权关系、一条广告主和两行报表快照。"""
    self_app = await _ensure_app(
        session,
        app_id=_SELF_APP_ID,
        channel="self",
        name="深圳发行中心-自研",
        secret=_SELF_SECRET_KEY,
        agent_key="1",
        agency=True,
        oauth_rid="c9lb3o12qhm",
    )
    third_app = await _ensure_app(
        session,
        app_id=_THIRD_APP_ID,
        channel="third",
        name="深圳发行中心-三方",
        secret=_THIRD_SECRET_KEY,
        agent_key="1",
        agency=False,
        oauth_rid="tg29ccnkpzm",
    )
    org = await _ensure_organization(session, self_app)
    await _ensure_organization(session, third_app)
    await _ensure_advertiser(session, self_app, org)
    await _ensure_report(session, promotion_id=8001, stat_cost=Decimal("120.00"), roi=Decimal("0.300"))
    await _ensure_report(session, promotion_id=8002, stat_cost=Decimal("10.00"), roi=Decimal("1.200"))
    await session.flush()


async def _ensure_app(
    session: AsyncSession,
    *,
    app_id: int,
    channel: str,
    name: str,
    secret: str,
    agent_key: str,
    agency: bool,
    oauth_rid: str,
) -> OeApp:
    found = await session.scalar(select(OeApp).where(OeApp.app_id == app_id))
    if found is not None:
        return found
    row = OeApp(
        channel=channel,
        name=name,
        app_id=app_id,
        secret=secret,
        agent_key=agent_key,
        agency=agency,
        material_auth=1,
        oauth_rid=oauth_rid,
        status="active",
    )
    session.add(row)
    await session.flush()
    return row


async def _ensure_organization(session: AsyncSession, app: OeApp) -> OeOrganization:
    """同一巨量账户只一行。每个应用再挂一条授权关系。"""
    found = await session.scalar(
        select(OeOrganization).where(
            OeOrganization.ocean_account_id == _ORG_OCEAN_ID,
            OeOrganization.is_deleted == 0,
        )
    )
    if found is None:
        found = OeOrganization(
            ocean_account_id=_ORG_OCEAN_ID,
            name="深圳发行中心",
            account_role="PLATFORM_ROLE_ENTERPRISE_BP_ADMIN",
            ocean_version="升级版组织",
            status="active",
        )
        session.add(found)
        await session.flush()
    elif found.account_role != "PLATFORM_ROLE_ENTERPRISE_BP_ADMIN":
        found.account_role = "PLATFORM_ROLE_ENTERPRISE_BP_ADMIN"
        found.ocean_version = "升级版组织"
    await _ensure_grant(session, found, app)
    return found


async def _ensure_grant(session: AsyncSession, org: OeOrganization, app: OeApp) -> None:
    found = await session.scalar(
        select(OeOrganizationGrant).where(
            OeOrganizationGrant.organization_id == org.id,
            OeOrganizationGrant.oe_app_id == app.id,
            OeOrganizationGrant.is_deleted == 0,
        )
    )
    if found is not None:
        return
    session.add(OeOrganizationGrant(organization_id=org.id, oe_app_id=app.id, status="active"))
    await session.flush()


async def _ensure_advertiser(session: AsyncSession, app: OeApp, org: OeOrganization) -> AdvertiserAccount:
    found = await session.scalar(
        select(AdvertiserAccount).where(AdvertiserAccount.advertiser_id == _ADVERTISER_ID)
    )
    if found is not None:
        return found
    now = beijing_now()
    row = AdvertiserAccount(
        organization_id=org.id,
        oe_app_id=app.id,
        advertiser_id=_ADVERTISER_ID,
        name="番茄漫剧测试户",
        valid_balance=Decimal("100.50"),
        company_name=_COMPANY_NAME,
        balance_synced_at=now,
        company_synced_at=now,
        sync_status="active",
    )
    session.add(row)
    await session.flush()
    return row


async def _ensure_report(
    session: AsyncSession,
    *,
    promotion_id: int,
    stat_cost: Decimal,
    roi: Decimal,
) -> None:
    found = await session.scalar(
        select(OeReportSnapshot.id).where(
            OeReportSnapshot.advertiser_id == _ADVERTISER_ID,
            OeReportSnapshot.promotion_id == promotion_id,
        )
    )
    if found is not None:
        return
    session.add(
        OeReportSnapshot(
            advertiser_id=_ADVERTISER_ID,
            promotion_id=promotion_id,
            stat_cost=stat_cost,
            attribution_micro_game_0d_roi=roi,
            synced_at=beijing_now(),
        )
    )
