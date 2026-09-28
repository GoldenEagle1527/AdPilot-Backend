"""巨量夹具对应的落库种子。只在调用时写库，import 不写。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.times import beijing_now
from app.modules.account.model import (
    AdvertiserAccount,
    DeliverySubject,
    DouyinAccount,
    DouyinPitcher,
    OeApp,
    OeOrganization,
    OeReportSnapshot,
    ProductLibrary,
    ProductLibraryPitcher,
)
from app.modules.system_admin.domain.models import UserTag, UserTagLink

# 配置键名，不是密钥明文。
_SELF_SECRET_KEY = "oceanengine.self.secret"
_THIRD_SECRET_KEY = "oceanengine.third.secret"

_COMPANY_NAME = "番茄漫剧~普通-我花-我家-低调-岁月-苏子-我替-我不-萌宝-重生-杭州瑶添IAA-常规-48-king-免费#2"

_SELF_APP_ID = 1870855836080240
_THIRD_APP_ID = 1870857293665690
_ORG_OCEAN_ID = 1872115109920903
_ADVERTISER_ID = 1873916032590219


async def ensure_oceanengine_seed(session: AsyncSession) -> None:
    """幂等插入两套应用、自研与三方各一条组织、一条广告主和两行报表快照。"""
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
    """同一巨量账户在每个应用下各一行。已有该应用上的这一行则不另插。"""
    found = await session.scalar(
        select(OeOrganization).where(
            OeOrganization.oe_app_id == app.id,
            OeOrganization.ocean_account_id == _ORG_OCEAN_ID,
        )
    )
    if found is not None:
        return found
    row = OeOrganization(
        oe_app_id=app.id,
        ocean_account_id=_ORG_OCEAN_ID,
        name="深圳发行中心",
        account_role="CUSTOMER_ADMIN",
        ocean_version="升级版组织",
        status="active",
    )
    session.add(row)
    await session.flush()
    return row


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


_DEMO_ADVERTISERS: tuple[dict[str, object], ...] = (
    {
        "advertiser_id": 9001001001,
        "name": "测试-番茄漫剧-未分配",
        "local_name": None,
        "valid_balance": Decimal("86.20"),
        "company_name": "杭州漆绘网络科技有限公司",
        "pitcher": False,
    },
    {
        "advertiser_id": 9001001002,
        "name": "测试-番茄漫剧-投手甲",
        "local_name": "投手甲专用户",
        "valid_balance": Decimal("1280.50"),
        "company_name": "杭州漆绘网络科技有限公司",
        "pitcher": True,
    },
    {
        "advertiser_id": 9001001003,
        "name": "测试-番茄漫剧-余额不足",
        "local_name": None,
        "valid_balance": Decimal("0.00"),
        "company_name": "杭州漆绘网络科技有限公司",
        "pitcher": True,
    },
)


async def ensure_frontend_demo(session: AsyncSession) -> None:
    """给已授权的真实应用补本地测试数据。已有同号则跳过。"""
    app = await session.scalar(select(OeApp).where(OeApp.app_id == 1877173761846616))
    if app is None:
        raise RuntimeError("配置的巨量应用还不在库里，先完成授权")
    org = await session.scalar(
        select(OeOrganization).where(
            OeOrganization.oe_app_id == app.id,
            OeOrganization.ocean_account_id == 1877115471075891,
            OeOrganization.is_deleted == 0,
        )
    )
    if org is None:
        raise RuntimeError("授权组织还不在库里")
    pitcher_tag = await session.scalar(select(UserTag).where(UserTag.name == "投手"))
    if pitcher_tag is not None:
        linked = await session.scalar(
            select(UserTagLink.id).where(
                UserTagLink.user_id == 3,
                UserTagLink.tag_id == pitcher_tag.id,
            )
        )
        if linked is None:
            session.add(UserTagLink(user_id=3, tag_id=pitcher_tag.id))
    now = beijing_now()
    accounts: dict[int, AdvertiserAccount] = {}
    for item in _DEMO_ADVERTISERS:
        advertiser_id = int(item["advertiser_id"])
        row = await session.scalar(
            select(AdvertiserAccount).where(AdvertiserAccount.advertiser_id == advertiser_id)
        )
        if row is None:
            row = AdvertiserAccount(
                organization_id=org.id,
                oe_app_id=app.id,
                advertiser_id=advertiser_id,
                name=str(item["name"]),
                local_name=item["local_name"] if isinstance(item["local_name"], str) else None,
                valid_balance=item["valid_balance"],
                company_name=str(item["company_name"]),
                balance_synced_at=now,
                company_synced_at=now,
                pitcher_user_id=3 if item["pitcher"] else None,
                assigned_at=now if item["pitcher"] else None,
                assigned_by="demo" if item["pitcher"] else None,
                sync_status="active",
            )
            session.add(row)
            await session.flush()
        accounts[advertiser_id] = row
    await _ensure_subject(
        session,
        subject_no=88001,
        name="测试主体-标准-IAA",
        short_name="标准IAA",
        delivery_mode="standard",
        charge_mode="IAA",
        material_account_id=accounts[9001001002].id,
        department_id=2,
        dual_bid=False,
        roi_goal=None,
    )
    await _ensure_subject(
        session,
        subject_no=88002,
        name="测试主体-全域-IAP",
        short_name="全域IAP",
        delivery_mode="uni",
        charge_mode="IAP",
        material_account_id=accounts[9001001003].id,
        department_id=None,
        dual_bid=True,
        roi_goal=Decimal("1.250"),
    )
    uni = await _ensure_douyin(
        session,
        aweme_id="demo_uni_01",
        name="测试全域号-投手甲",
        delivery_mode="uni",
        department_id=2,
        owner_user_id=1,
    )
    await _ensure_douyin(
        session,
        aweme_id="demo_std_01",
        name="测试标准号-共用",
        delivery_mode="standard",
        department_id=None,
        owner_user_id=None,
    )
    if uni is not None:
        linked_pitcher = await session.scalar(
            select(DouyinPitcher.id).where(
                DouyinPitcher.douyin_account_id == uni.id,
                DouyinPitcher.user_id == 3,
            )
        )
        if linked_pitcher is None:
            session.add(DouyinPitcher(douyin_account_id=uni.id, user_id=3))
    video_fallback = await _ensure_library(
        session,
        org_id=org.id,
        library_no=77001,
        name="测试视频兜底库",
        library_kind="video",
        library_role="fallback",
    )
    video_standard = await _ensure_library(
        session,
        org_id=org.id,
        library_no=77002,
        name="测试视频标准库",
        library_kind="video",
        library_role="standard",
    )
    await _ensure_library(
        session,
        org_id=org.id,
        library_no=77003,
        name="测试小说兜底库",
        library_kind="novel",
        library_role="fallback",
    )
    if video_standard is not None:
        assigned = await session.scalar(
            select(ProductLibraryPitcher.id).where(
                ProductLibraryPitcher.user_id == 3,
                ProductLibraryPitcher.organization_id == org.id,
                ProductLibraryPitcher.library_kind == "video",
            )
        )
        if assigned is None:
            session.add(
                ProductLibraryPitcher(
                    product_library_id=video_standard.id,
                    user_id=3,
                    organization_id=org.id,
                    library_kind="video",
                )
            )
    await session.flush()
    del video_fallback


async def _ensure_subject(
    session: AsyncSession,
    *,
    subject_no: int,
    name: str,
    short_name: str,
    delivery_mode: str,
    charge_mode: str,
    material_account_id: int,
    department_id: int | None,
    dual_bid: bool,
    roi_goal: Decimal | None,
) -> None:
    found = await session.scalar(select(DeliverySubject).where(DeliverySubject.subject_no == subject_no))
    if found is not None:
        return
    session.add(
        DeliverySubject(
            name=name,
            subject_no=subject_no,
            short_name=short_name,
            delivery_mode=delivery_mode,
            theater_name="番茄",
            theater_kind="端原生",
            charge_mode=charge_mode,
            min_bid=Decimal("1.00"),
            max_bid=Decimal("30.00"),
            roi_goal=roi_goal,
            department_id=department_id,
            material_account_id=material_account_id,
            dual_bid=dual_bid,
            bid_panel="测试面板",
        )
    )


async def _ensure_douyin(
    session: AsyncSession,
    *,
    aweme_id: str,
    name: str,
    delivery_mode: str,
    department_id: int | None,
    owner_user_id: int | None,
) -> DouyinAccount | None:
    found = await session.scalar(
        select(DouyinAccount).where(
            DouyinAccount.aweme_id == aweme_id,
            DouyinAccount.delivery_mode == delivery_mode,
        )
    )
    if found is not None:
        return found
    row = DouyinAccount(
        aweme_id=aweme_id,
        name=name,
        delivery_mode=delivery_mode,
        enabled=True,
        department_id=department_id,
        owner_user_id=owner_user_id,
        created_by="demo",
    )
    session.add(row)
    await session.flush()
    return row


async def _ensure_library(
    session: AsyncSession,
    *,
    org_id: int,
    library_no: int,
    name: str,
    library_kind: str,
    library_role: str,
) -> ProductLibrary | None:
    found = await session.scalar(select(ProductLibrary).where(ProductLibrary.library_no == library_no))
    if found is not None:
        return found
    row = ProductLibrary(
        name=name,
        library_no=library_no,
        library_kind=library_kind,
        organization_id=org_id,
        library_role=library_role,
        uploaded_count=0,
    )
    session.add(row)
    await session.flush()
    return row
