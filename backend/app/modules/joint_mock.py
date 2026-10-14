"""mock 启动时的一份业务夹具。按稳定业务键插入或纠正，重复启动不复制行。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.times import BEIJING, beijing_now
from app.modules.account.model import (
    AdvertiserAccount,
    DeliverySubject,
    DouyinAccount,
    DouyinPitcher,
    OeApp,
    OeMaterialReport,
    OeOrganization,
    OeOrganizationGrant,
    OeProject,
    OePromotion,
    OeReportSnapshot,
    OeUniProjectReport,
    ProductLibrary,
    ProductLibraryPitcher,
)
from app.modules.material.model import ManhuaSeries
from app.modules.material_title.model import MaterialTitle, TitleCategory
from app.modules.material_video.model import (
    MaterialType,
    MaterialVideo,
    MaterialVideoPitcher,
    MaterialVideoTag,
    Ownership,
    Platform,
)
from app.modules.ocean_ads.mock_seed import project_template, uni_hour_rows
from app.modules.oceanengine.delivery_report import pull_days
from app.modules.report.refresh import rebuild_serving
from app.modules.report.serving import ReportProfitDay, ReportRoiConfig
from app.modules.standard_delivery.model import (
    DeliveryAutoRule,
    DeliveryAutoRuleSeries,
    DeliveryTaskAccount,
    DeliveryTaskDraft,
    DeliveryTaskProject,
    DeliveryTaskPromotion,
    DeliveryTemplate,
)
from app.modules.standard_robot.model import StandardNativeRobotRule
from app.modules.system_admin.domain.models import UserTag, UserTagLink
from app.modules.theater.model import (
    TheaterApp,
    TheaterPlatform,
    TheaterPromotionLink,
    TheaterPromotionTask,
)
from app.modules.uni_native_task.model import NativeTaskStatus, UniNativeTask, UniNativeTaskAccount
from app.modules.uni_robot.model import UniRobotRule

_PITCHER_ID = 3
_SELF_SECRET_KEY = "oceanengine.self.secret"
_THIRD_SECRET_KEY = "oceanengine.third.secret"
_SEED_COMPANY = "番茄漫剧~普通-我花-我家-低调-岁月-苏子-我替-我不-萌宝-重生-杭州瑶添IAA-常规-48-king-免费#2"
_SELF_APP_ID = 1870855836080240
_THIRD_APP_ID = 1870857293665690
_SEED_ORG = 1872115109920903
_SEED_ADVERTISER = 1873916032590219
_PULLED_ADVERTISER = 1877368580368602
_HAOYUN_ORG = 1877115471075891
_PANEL_COMPANY = "杭州瑶添文化传媒有限公司"
_DEMO_ADVERTISERS = (9001001001, 9001001002, 9001001003)
_SEED_PROJECT = 80010001
_PULLED_PROJECT = 7691188278174826546
_UNI_PROJECT = 80030001
_UNI_PROMOTION = 80030002
_UNI_MATERIAL = 80030003
_UNI_PROJECT_NAME = "全域夹具项目"
_UNI_PROMOTION_NAME = "全域夹具广告"
_UNI_HOUR_NAME = "深山_付费_UBA_09-30 12:59_6131"
_STD_DOUYIN = "demo_std_01"
_UNI_DOUYIN = "demo_uni_01"

_PANEL_ADVERTISERS = (
    (1873916032590301, "番茄漫剧-广告主甲", "广告主甲", Decimal("1280.50")),
    (1873916032590302, "番茄漫剧-广告主乙", "广告主乙", Decimal("860.00")),
    (1873916032590303, "番茄漫剧-广告主丙", "广告主丙", Decimal("320.75")),
    (1873916032590304, "番茄漫剧-广告主丁", "广告主丁", Decimal("56.20")),
)

# 模板 id -> 主体 subject_no。只改未软删模板的 subject_id。
_TEMPLATE_SUBJECTS = {5: 88001, 6: 88001, 7: 12555, 10: 88002, 12: 88002, 15: 88002}

_STANDARD_TASKS = (
    {
        "ocean_project_id": _SEED_PROJECT,
        "promotion_ids": (8001, 8002),
        "advertiser_id": _SEED_ADVERTISER,
        "template_id": 5,
        "series_id": 2,
        "charge_mode": "IAA",
        "optimize_goal": "AD_CONVERT_TYPE_ACTIVE",
        "panel": "",
        "project_budget": Decimal("300.00"),
    },
    {
        "ocean_project_id": _PULLED_PROJECT,
        "promotion_ids": (7691188146411814975, 7691188154167427115),
        "advertiser_id": _PULLED_ADVERTISER,
        "template_id": 7,
        "series_id": 1,
        "charge_mode": "IAP",
        "optimize_goal": "AD_CONVERT_TYPE_PAY",
        "panel": "中额",
        "project_budget": Decimal("800.00"),
    },
)

# 消耗、总成本、GMV、收入、当日收入、付费收入、变现收入、展示、点击。三个计费 GMV 等于该行 GMV。
_UNI_HOUR_FACTS = (
    ("2026-10-11 10:00:00", "130.00", "130.00", "182.00", "127.40", "127.40", "72.80", "54.60", 1300, 130),
    ("2026-10-11 14:00:00", "134.00", "134.00", "187.60", "131.32", "131.32", "75.04", "56.28", 1340, 134),
    ("2026-10-11 18:00:00", "138.00", "138.00", "193.20", "135.24", "135.24", "77.28", "57.96", 1380, 138),
    ("2026-10-11 21:00:00", "141.00", "141.00", "197.40", "138.18", "138.18", "78.96", "59.22", 1410, 141),
    ("2026-10-12 10:00:00", "150.00", "150.00", "210.00", "147.00", "147.00", "84.00", "63.00", 1500, 150),
    ("2026-10-12 14:00:00", "154.00", "154.00", "215.60", "150.92", "150.92", "86.24", "64.68", 1540, 154),
    ("2026-10-12 18:00:00", "158.00", "158.00", "221.20", "154.84", "154.84", "88.48", "66.36", 1580, 158),
    ("2026-10-12 21:00:00", "161.00", "161.00", "225.40", "157.78", "157.78", "90.16", "67.62", 1610, 161),
    ("2026-10-13 10:00:00", "170.00", "170.00", "238.00", "166.60", "166.60", "95.20", "71.40", 1700, 170),
    ("2026-10-13 14:00:00", "174.00", "174.00", "243.60", "170.52", "170.52", "97.44", "73.08", 1740, 174),
    ("2026-10-13 18:00:00", "178.00", "178.00", "249.20", "174.44", "174.44", "99.68", "74.76", 1780, 178),
    ("2026-10-13 21:00:00", "181.00", "181.00", "253.40", "177.38", "177.38", "101.36", "76.02", 1810, 181),
)

_PROFIT_ROWS = (
    (date(2026, 10, 1), "IAP", Decimal("1307.58"), Decimal("1044.54")),
    (date(2026, 10, 2), "IAP", Decimal("107.34"), Decimal("11.32")),
    (date(2026, 10, 3), "IAP", Decimal("13.90"), Decimal("0.00")),
    (date(2026, 10, 4), "IAP", Decimal("0.20"), Decimal("0.00")),
    (date(2026, 10, 12), "IAA", Decimal("254.00"), Decimal("106.68")),
    (date(2026, 10, 12), "IAP", Decimal("407.00"), Decimal("170.94")),
    (date(2026, 10, 13), "IAA", Decimal("302.00"), Decimal("126.84")),
    (date(2026, 10, 13), "IAP", Decimal("455.00"), Decimal("191.10")),
    (date(2026, 10, 14), "IAA", Decimal("350.00"), Decimal("147.00")),
    (date(2026, 10, 14), "IAP", Decimal("503.00"), Decimal("211.26")),
)

_ID_TABLES = (
    "manhua_series",
    "theater_platforms",
    "theater_apps",
    "theater_promotion_tasks",
    "theater_promotion_links",
    "standard_native_robot_rule",
    "uni_robot_rule",
    "delivery_auto_rule",
    "delivery_auto_rule_series",
)


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _dec(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


async def ensure_joint_mock(session: AsyncSession) -> None:
    """写入夹具并 flush，刷近 8 天日表，再按唯一键纠正利润和 ROI。"""
    await _ensure_user_tags(session)
    await _ensure_account_seed(session)
    await _ensure_advertisers(session)
    await _ensure_series(session)
    await _ensure_subjects(session)
    await _ensure_template_subjects(session)
    std_douyin, uni_douyin = await _ensure_douyin(session)
    await _ensure_platforms(session)
    await _ensure_theater_apps(session)
    await _ensure_promotion_links(session)
    await _ensure_standard_tasks(session, std_douyin)
    await _ensure_uni_task(session, uni_douyin)
    await _ensure_oe_projects(session, std_douyin, uni_douyin)
    await _ensure_hours(session)
    await _ensure_libraries(session)
    await _ensure_robots(session)
    await _ensure_materials(session)
    await session.flush()
    await _advance_sequences(session)
    await rebuild_serving(session, pull_days(beijing_now()))
    await _ensure_profit(session)
    await _ensure_roi(session)
    await session.commit()


async def _ensure_user_tags(session: AsyncSession) -> None:
    """用户 3 挂上「短剧投手」和已有的「投手」。不新建用户。"""
    drama = await session.scalar(select(UserTag).where(UserTag.name == "短剧投手"))
    if drama is None:
        drama = UserTag(name="短剧投手")
        session.add(drama)
        await session.flush()
    elif drama.is_deleted:
        drama.is_deleted = 0
        drama.deleted_at = None
    pitcher = await session.scalar(select(UserTag).where(UserTag.name == "投手"))
    for tag in (drama, pitcher):
        if tag is None:
            continue
        link = await session.scalar(
            select(UserTagLink).where(UserTagLink.user_id == _PITCHER_ID, UserTagLink.tag_id == tag.id)
        )
        if link is None:
            session.add(UserTagLink(user_id=_PITCHER_ID, tag_id=tag.id))
        elif link.is_deleted:
            link.is_deleted = 0
            link.deleted_at = None


async def _ensure_account_seed(session: AsyncSession) -> None:
    """两套应用、一条活组织、两条授权、广告主和两行快照。已有不复制，软删组织不复活。"""
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
    org = await _ensure_seed_org(session, self_app)
    await _ensure_seed_org(session, third_app)
    await _ensure_seed_advertiser(session, self_app, org)
    await _ensure_snapshot(session, promotion_id=8001, stat_cost=Decimal("120.00"), roi=Decimal("0.300"))
    await _ensure_snapshot(session, promotion_id=8002, stat_cost=Decimal("10.00"), roi=Decimal("1.200"))
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


async def _ensure_seed_org(session: AsyncSession, app: OeApp) -> OeOrganization:
    found = await session.scalar(
        select(OeOrganization).where(
            OeOrganization.ocean_account_id == _SEED_ORG,
            OeOrganization.is_deleted == 0,
        )
    )
    if found is None:
        found = OeOrganization(
            ocean_account_id=_SEED_ORG,
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


async def _ensure_seed_advertiser(session: AsyncSession, app: OeApp, org: OeOrganization) -> None:
    found = await _advertiser(session, _SEED_ADVERTISER)
    if found is not None:
        return
    now = beijing_now()
    session.add(
        AdvertiserAccount(
            organization_id=org.id,
            oe_app_id=app.id,
            advertiser_id=_SEED_ADVERTISER,
            name="番茄漫剧测试户",
            valid_balance=Decimal("100.50"),
            company_name=_SEED_COMPANY,
            balance_synced_at=now,
            company_synced_at=now,
            sync_status="active",
        )
    )
    await session.flush()


async def _ensure_snapshot(session: AsyncSession, *, promotion_id: int, stat_cost: Decimal, roi: Decimal) -> None:
    found = await session.scalar(
        select(OeReportSnapshot.id).where(
            OeReportSnapshot.advertiser_id == _SEED_ADVERTISER,
            OeReportSnapshot.promotion_id == promotion_id,
        )
    )
    if found is not None:
        return
    session.add(
        OeReportSnapshot(
            advertiser_id=_SEED_ADVERTISER,
            promotion_id=promotion_id,
            stat_cost=stat_cost,
            attribution_micro_game_0d_roi=roi,
            synced_at=beijing_now(),
        )
    )


async def _ensure_advertisers(session: AsyncSession) -> None:
    """纠正投手和软删。缺的广告主按备份名称、余额挂到未软删的授权组织。"""
    await _open_advertiser(session, _SEED_ADVERTISER, pitcher_user_id=_PITCHER_ID)
    await _ensure_placed_advertiser(
        session,
        ocean_id=_PULLED_ADVERTISER,
        name="报表夹具广告主",
        local_name=None,
        balance=Decimal("100.00"),
        company="报表夹具",
        pitcher_user_id=_PITCHER_ID,
        prefer_org=_SEED_ORG,
    )
    for ocean_id, name, local_name, balance in _PANEL_ADVERTISERS:
        await _ensure_placed_advertiser(
            session,
            ocean_id=ocean_id,
            name=name,
            local_name=local_name,
            balance=balance,
            company=_PANEL_COMPANY,
            pitcher_user_id=None,
            prefer_org=_HAOYUN_ORG,
        )
    for ocean_id in _DEMO_ADVERTISERS:
        rows = list(
            await session.scalars(select(AdvertiserAccount).where(AdvertiserAccount.advertiser_id == ocean_id))
        )
        for row in rows:
            if row.is_deleted == 0:
                row.mark_deleted()
    await session.flush()


async def _open_advertiser(session: AsyncSession, ocean_id: int, *, pitcher_user_id: int | None) -> None:
    row = await _advertiser(session, ocean_id)
    if row is None:
        return
    row.is_deleted = 0
    row.deleted_at = None
    row.pitcher_user_id = pitcher_user_id


async def _ensure_placed_advertiser(
    session: AsyncSession,
    *,
    ocean_id: int,
    name: str,
    local_name: str | None,
    balance: Decimal,
    company: str,
    pitcher_user_id: int | None,
    prefer_org: int,
) -> AdvertiserAccount:
    found = await _advertiser(session, ocean_id)
    if found is not None:
        found.is_deleted = 0
        found.deleted_at = None
        found.pitcher_user_id = pitcher_user_id
        return found
    placed = await _granted_org(session, prefer_org)
    if placed is None:
        raise RuntimeError(f"没有未软删的授权组织可挂广告主 {ocean_id}")
    org, grant = placed
    now = beijing_now()
    row = AdvertiserAccount(
        organization_id=org.id,
        oe_app_id=grant.oe_app_id,
        advertiser_id=ocean_id,
        name=name,
        local_name=local_name,
        valid_balance=balance,
        company_name=company,
        balance_synced_at=now,
        company_synced_at=now,
        pitcher_user_id=pitcher_user_id,
        sync_status="active",
    )
    session.add(row)
    await session.flush()
    return row


async def _advertiser(session: AsyncSession, ocean_id: int) -> AdvertiserAccount | None:
    return await session.scalar(
        select(AdvertiserAccount)
        .where(AdvertiserAccount.advertiser_id == ocean_id)
        .order_by(AdvertiserAccount.is_deleted, AdvertiserAccount.id)
        .limit(1)
    )


async def _granted_org(
    session: AsyncSession, prefer_ocean_id: int | None
) -> tuple[OeOrganization, OeOrganizationGrant] | None:
    """优先指定巨量组织；否则任一未软删且有未软删授权的组织。"""
    if prefer_ocean_id is not None:
        preferred = await session.scalar(
            select(OeOrganization).where(
                OeOrganization.ocean_account_id == prefer_ocean_id,
                OeOrganization.is_deleted == 0,
            )
        )
        if preferred is not None:
            grant = await _org_grant(session, preferred.id)
            if grant is not None:
                return preferred, grant
    org_ids = list(
        await session.scalars(
            select(OeOrganization.id)
            .join(OeOrganizationGrant, OeOrganizationGrant.organization_id == OeOrganization.id)
            .where(OeOrganization.is_deleted == 0, OeOrganizationGrant.is_deleted == 0)
            .order_by(OeOrganization.id)
            .distinct()
        )
    )
    for org_id in org_ids:
        grant = await _org_grant(session, org_id)
        if grant is None:
            continue
        org = await session.get(OeOrganization, org_id)
        if org is not None:
            return org, grant
    return None


async def _org_grant(session: AsyncSession, org_id: int) -> OeOrganizationGrant | None:
    grants = list(
        await session.scalars(
            select(OeOrganizationGrant)
            .where(OeOrganizationGrant.organization_id == org_id, OeOrganizationGrant.is_deleted == 0)
            .order_by(OeOrganizationGrant.id)
        )
    )
    if not grants:
        return None
    for grant in grants:
        app = await session.get(OeApp, grant.oe_app_id)
        if app is not None and app.channel == "self":
            return grant
    return grants[0]


async def _ensure_subjects(session: AsyncSession) -> None:
    """已有主体只改素材账户。没有才插入。素材账户不指向 9001001001–003。"""
    seed = await _require_advertiser(session, _SEED_ADVERTISER)
    pulled = await _require_advertiser(session, _PULLED_ADVERTISER)
    await _ensure_subject(
        session,
        subject_no=88001,
        material_account_id=seed.id,
        name="测试主体-标准-IAA",
        short_name="标准IAA",
        delivery_mode="standard",
        charge_mode="IAA",
        department_id=2,
        dual_bid=False,
        roi_goal=None,
        theater_name="番茄",
        theater_kind="端原生",
        min_bid=Decimal("1.00"),
        max_bid=Decimal("30.00"),
        bid_panel="测试面板",
    )
    await _ensure_subject(
        session,
        subject_no=12555,
        material_account_id=pulled.id,
        name="测试主体",
        short_name=None,
        delivery_mode="standard",
        charge_mode="IAP",
        department_id=2,
        dual_bid=True,
        roi_goal=None,
        theater_name="番茄漫剧收费",
        theater_kind="端原生",
        min_bid=Decimal("5.00"),
        max_bid=Decimal("87.00"),
        bid_panel="中额",
    )
    await _ensure_subject(
        session,
        subject_no=88002,
        material_account_id=pulled.id,
        name="测试主体-全域-IAP",
        short_name="全域IAP",
        delivery_mode="uni",
        charge_mode="IAP",
        department_id=None,
        dual_bid=True,
        roi_goal=Decimal("1.250"),
        theater_name="番茄",
        theater_kind="端原生",
        min_bid=Decimal("1.00"),
        max_bid=Decimal("30.00"),
        bid_panel="测试面板",
    )


async def _ensure_subject(session: AsyncSession, *, subject_no: int, material_account_id: int, **columns: object) -> DeliverySubject:
    alive = await session.scalar(
        select(DeliverySubject).where(DeliverySubject.subject_no == subject_no, DeliverySubject.is_deleted == 0)
    )
    if alive is not None:
        alive.material_account_id = material_account_id
        return alive
    row = DeliverySubject(subject_no=subject_no, material_account_id=material_account_id, **columns)
    session.add(row)
    await session.flush()
    return row


async def _require_advertiser(session: AsyncSession, ocean_id: int) -> AdvertiserAccount:
    row = await _advertiser(session, ocean_id)
    if row is None:
        raise RuntimeError(f"广告主 {ocean_id} 不在库里")
    return row


async def _subject_id(session: AsyncSession, subject_no: int) -> int:
    row = await session.scalar(
        select(DeliverySubject).where(DeliverySubject.subject_no == subject_no, DeliverySubject.is_deleted == 0)
    )
    if row is None:
        raise RuntimeError(f"主体 {subject_no} 不在库里")
    return row.id


async def _ensure_template_subjects(session: AsyncSession) -> None:
    """未软删模板只改 subject_id。已软删的不复活，缺模板不新建。"""
    for template_id, subject_no in _TEMPLATE_SUBJECTS.items():
        template = await session.get(DeliveryTemplate, template_id)
        if template is None or template.is_deleted != 0:
            continue
        template.subject_id = await _subject_id(session, subject_no)


async def _ensure_douyin(session: AsyncSession) -> tuple[DouyinAccount, DouyinAccount]:
    """没有 demo_std_01 / demo_uni_01 才按演示脚本插入。已有不改。"""
    standard = await _douyin(
        session,
        aweme_id=_STD_DOUYIN,
        name="测试标准号-共用",
        delivery_mode="standard",
        department_id=None,
        owner_user_id=None,
    )
    uni = await _douyin(
        session,
        aweme_id=_UNI_DOUYIN,
        name="测试全域号-投手甲",
        delivery_mode="uni",
        department_id=2,
        owner_user_id=1,
    )
    linked = await session.scalar(
        select(DouyinPitcher.id).where(DouyinPitcher.douyin_account_id == uni.id, DouyinPitcher.user_id == _PITCHER_ID)
    )
    if linked is None:
        session.add(DouyinPitcher(douyin_account_id=uni.id, user_id=_PITCHER_ID))
    await session.flush()
    return standard, uni


async def _douyin(
    session: AsyncSession,
    *,
    aweme_id: str,
    name: str,
    delivery_mode: str,
    department_id: int | None,
    owner_user_id: int | None,
) -> DouyinAccount:
    found = await session.scalar(
        select(DouyinAccount)
        .where(DouyinAccount.aweme_id == aweme_id, DouyinAccount.delivery_mode == delivery_mode)
        .order_by(DouyinAccount.is_deleted, DouyinAccount.id)
        .limit(1)
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


async def _ensure_series(session: AsyncSession) -> None:
    """短剧 1–6。id 已在就不改正文、不复活。没有才按备份列插入，名称用夹具名。"""
    for row in _series_rows():
        found = await session.get(ManhuaSeries, row["id"])
        if found is not None:
            continue
        session.add(ManhuaSeries(**row))
    await session.flush()


def _series_rows() -> list[dict[str, object]]:
    collected = _ts("2026-10-09 06:20:02.900891+00")
    names = ("玄幻逆袭", "都市神医", "甜宠日常", "悬疑反转", "古言权谋", "科幻末世")
    raw = (
        ("https://example.com/cover/xuanhuan.jpg", 80, 1, "玄幻脑洞,逆袭", 2, "2026-10-09 10:00:00", "2026-10-09 02:00:00+00", 1, "2026-10-01 09:00:00", "0", "演示数据：免费投放，页签为 IAA。", True, "IAA"),
        ("https://example.com/cover/dushi.jpg", 60, 1, "都市,神医", 2, "2026-09-01 09:00:00", "2026-09-01 01:00:00+00", 1, "2026-08-20 09:00:00", "9.9", "演示数据：收费投放，页签为 IAP。", True, "IAP"),
        ("https://example.com/cover/tianchong.jpg", 40, 2, "甜宠,日常", 1, "2026-10-08 18:30:00", "2026-10-08 10:30:00+00", 1, "2026-09-01 09:00:00", "0", "演示数据：未发布，页签为 IAA。", False, "IAA"),
        ("https://example.com/cover/xuanyi.jpg", 24, 0, "悬疑,反转", 3, "2026-09-15 12:00:00", "2026-09-15 04:00:00+00", 0, "2026-09-01 09:00:00", "1", "演示数据：已下架，页签为 IAP。", False, "IAP"),
        ("https://example.com/cover/guyan.jpg", 72, 2, "古言,权谋", 2, "2026-10-02 08:00:00", "2026-10-02 00:00:00+00", 1, "2026-09-20 08:00:00", "6.6", "演示数据：收费投放，页签为 IAP。", True, "IAP"),
        ("https://example.com/cover/kehuan.jpg", 36, 1, "科幻,末世", 2, "2026-10-05 20:00:00", "2026-10-05 12:00:00+00", 1, "2026-09-28 20:00:00", "0", "演示数据：免费投放，页签为 IAA。", True, "IAA"),
    )
    rows: list[dict[str, object]] = []
    for index, item in enumerate(raw, start=1):
        book_id = 9100000000 + index
        rows.append(
            {
                "id": index,
                "book_name": names[index - 1],
                "book_id": book_id,
                "playlet_id": book_id,
                "thumb_url": item[0],
                "episode_amount": item[1],
                "gender": item[2],
                "category_text": item[3],
                "publish_status": item[4],
                "publish_time": item[5],
                "estimate_publish_time": _ts(item[6]),
                "permission_status": item[7],
                "create_time": item[8],
                "douyin_nick_name": "演示剧场",
                "single_price": item[9],
                "abstract": item[10],
                "delivery_status": item[11],
                "collected_at": collected,
                "tab_text": item[12],
                "promotion_triggered": True,
            }
        )
    return rows


async def _ensure_platforms(session: AsyncSession) -> None:
    """按 id 补番茄和鸥溪。已有该 id 不改正文。"""
    specs = (
        (1, "番茄", "1011", 1),
        (22, "鸥溪", "4504", 2),
    )
    for platform_id, name, code, sort_order in specs:
        if await session.get(TheaterPlatform, platform_id) is not None:
            continue
        session.add(
            TheaterPlatform(
                id=platform_id,
                name=name,
                code=code,
                sort_order=sort_order,
                is_enabled=True,
                supports_mini_program=False,
                supports_native=True,
            )
        )
    await session.flush()


async def _ensure_theater_apps(session: AsyncSession) -> None:
    """剧场应用 1、2。缺了才插，平台都是番茄 1。已有未删不改正文，不复活软删。"""
    specs = (
        (1, "番茄漫剧免费", "IAA"),
        (2, "番茄漫剧付费", "IAP"),
    )
    for app_id, name, delivery_mode in specs:
        if await session.get(TheaterApp, app_id) is not None:
            continue
        session.add(
            TheaterApp(
                id=app_id,
                platform_id=1,
                name=name,
                theater_type="native",
                delivery_mode=delivery_mode,
                style="manhua",
                ad_source="本地剧场",
                is_valid=True,
            )
        )
    await session.flush()


async def _ensure_promotion_links(session: AsyncSession) -> None:
    """mock.local 的 7 条推广链。缺链时连任务行一起补。已有链不改。"""
    for task in _promotion_tasks():
        if await session.get(TheaterPromotionTask, task["id"]) is not None:
            continue
        session.add(TheaterPromotionTask(**task))
    await session.flush()
    for link in _promotion_links():
        found = await session.scalar(
            select(TheaterPromotionLink.id).where(TheaterPromotionLink.promotion_id == link["promotion_id"])
        )
        if found is not None or await session.get(TheaterPromotionLink, link["id"]) is not None:
            continue
        session.add(TheaterPromotionLink(**link))
    await session.flush()


def _promotion_tasks() -> list[dict[str, object]]:
    shared_execute = _ts("2026-10-12 02:26:03.584896+00")
    rows = (
        (2, 1, None, "auto", shared_execute, _ts("2026-10-12 02:26:03.836756+00"), None),
        (3, 2, None, "auto", shared_execute, _ts("2026-10-12 02:26:03.841929+00"), None),
        (4, 3, None, "auto", shared_execute, _ts("2026-10-12 02:26:03.841403+00"), None),
        (5, 4, None, "auto", shared_execute, _ts("2026-10-12 02:26:03.842452+00"), None),
        (6, 5, None, "auto", shared_execute, _ts("2026-10-12 02:26:03.842986+00"), None),
        (7, 6, None, "auto", shared_execute, _ts("2026-10-12 02:26:03.948108+00"), None),
        (8, 6, 1, "manual", _ts("2026-10-12 02:00:00+00"), _ts("2026-10-12 02:27:04.533288+00"), "all"),
    )
    return [
        {
            "id": task_id,
            "series_id": series_id,
            "collector_id": collector_id,
            "source": source,
            "status": "success",
            "reason": "",
            "execute_at": execute_at,
            "finished_at": finished_at,
            "retry_count": 0,
            "charge_filter": charge_filter,
        }
        for task_id, series_id, collector_id, source, execute_at, finished_at, charge_filter in rows
    ]


def _promotion_links() -> list[dict[str, object]]:
    publish = _ts("2026-10-10 00:00:00+00")
    created = _ts("2026-10-10 04:00:00+00")
    rows = (
        (1, 1, 1, 2, 91000000013, "IAA", 3),
        (2, 1, 3, 4, 91000000033, "IAA", 3),
        (3, 2, 2, 3, 91000000022, "中额", 2),
        (4, 2, 4, 5, 91000000042, "中额", 2),
        (5, 2, 5, 6, 91000000052, "中额", 2),
        (6, 1, 6, 7, 91000000063, "IAA", 3),
        (7, 2, 6, 8, 91000000062, "中额", 2),
    )
    return [
        {
            "id": link_id,
            "theater_app_id": app_id,
            "series_id": series_id,
            "task_id": task_id,
            "source": "api",
            "promotion_id": promotion_id,
            "promotion_url": f"https://mock.local/p/{promotion_id}",
            "recharge_template_name": panel,
            "media_config_type": media,
            "publish_time": publish,
            "promotion_create_time": created,
            "package_app_key": "mock",
            "is_enabled": True,
        }
        for link_id, app_id, series_id, task_id, promotion_id, panel, media in rows
    ]


async def _ensure_standard_tasks(session: AsyncSession, douyin: DouyinAccount) -> None:
    """未软删的标准项目只纠正模板、剧、抖音、广告主和列出的广告号。没有才插一条。"""
    for spec in _STANDARD_TASKS:
        ocean_project_id = int(spec["ocean_project_id"])
        alive = await session.scalar(
            select(DeliveryTaskProject).where(
                DeliveryTaskProject.ocean_project_id == ocean_project_id,
                DeliveryTaskProject.is_deleted == 0,
            )
        )
        advertiser = await _require_advertiser(session, int(spec["advertiser_id"]))
        if alive is not None:
            await _correct_standard_task(session, alive, spec, advertiser, douyin)
            continue
        occupied = await session.scalar(
            select(DeliveryTaskProject.id).where(DeliveryTaskProject.ocean_project_id == ocean_project_id)
        )
        if occupied is not None:
            continue
        await _insert_standard_task(session, spec, advertiser, douyin)


async def _correct_standard_task(
    session: AsyncSession,
    project: DeliveryTaskProject,
    spec: dict[str, object],
    advertiser: AdvertiserAccount,
    douyin: DouyinAccount,
) -> None:
    draft = await session.get(DeliveryTaskDraft, project.task_id)
    if draft is not None and draft.is_deleted == 0:
        draft.template_id = int(spec["template_id"])
        draft.series_id = int(spec["series_id"])
        draft.douyin_account_id = douyin.id
    accounts = list(
        await session.scalars(
            select(DeliveryTaskAccount).where(
                DeliveryTaskAccount.task_id == project.task_id,
                DeliveryTaskAccount.is_deleted == 0,
            )
        )
    )
    chosen = next((row for row in accounts if row.ocean_project_id == project.ocean_project_id), None)
    if chosen is None:
        chosen = next((row for row in accounts if row.advertiser_account_id == project.advertiser_account_id), None)
    if chosen is None and len(accounts) == 1:
        chosen = accounts[0]
    if chosen is not None and chosen.advertiser_account_id != advertiser.id:
        clash = any(row.id != chosen.id and row.advertiser_account_id == advertiser.id for row in accounts)
        if not clash:
            chosen.advertiser_account_id = advertiser.id
    project.advertiser_account_id = advertiser.id
    await _fill_task_promotions(session, project.id, tuple(spec["promotion_ids"]))


async def _insert_standard_task(
    session: AsyncSession,
    spec: dict[str, object],
    advertiser: AdvertiserAccount,
    douyin: DouyinAccount,
) -> None:
    promotion_ids = tuple(spec["promotion_ids"])
    ocean_project_id = int(spec["ocean_project_id"])
    draft = DeliveryTaskDraft(
        template_id=int(spec["template_id"]),
        charge_mode=str(spec["charge_mode"]),
        pitcher_user_id=_PITCHER_ID,
        series_id=int(spec["series_id"]),
        douyin_account_id=douyin.id,
        project_budget=spec["project_budget"],
        ad_budget=Decimal("100.00"),
        optimize_goal=str(spec["optimize_goal"]),
        submitted_at=beijing_now(),
    )
    session.add(draft)
    await session.flush()
    session.add(
        DeliveryTaskAccount(
            task_id=draft.id,
            advertiser_account_id=advertiser.id,
            sort_order=0,
            ocean_project_id=ocean_project_id,
        )
    )
    project = DeliveryTaskProject(
        task_id=draft.id,
        advertiser_account_id=advertiser.id,
        bid_panel=str(spec["panel"]),
        ocean_project_id=ocean_project_id,
        sort_order=0,
    )
    session.add(project)
    await session.flush()
    await _fill_task_promotions(session, project.id, promotion_ids)


async def _fill_task_promotions(session: AsyncSession, task_project_id: int, promotion_ids: tuple[int, ...]) -> None:
    existing = list(
        await session.scalars(
            select(DeliveryTaskPromotion).where(DeliveryTaskPromotion.task_project_id == task_project_id)
        )
    )
    have = {int(row.ocean_promotion_id) for row in existing}
    next_sort = max((row.sort_order for row in existing), default=-1) + 1
    for promotion_id in promotion_ids:
        if promotion_id in have:
            continue
        taken = await session.scalar(
            select(DeliveryTaskPromotion.id).where(DeliveryTaskPromotion.ocean_promotion_id == promotion_id)
        )
        if taken is not None:
            continue
        session.add(
            DeliveryTaskPromotion(
                task_project_id=task_project_id,
                ocean_promotion_id=promotion_id,
                sort_order=next_sort,
            )
        )
        next_sort += 1


async def _ensure_uni_task(session: AsyncSession, douyin: DouyinAccount) -> None:
    """旧项目号或 80030001 的未软删账户行原地改。两种都没有才插一条。"""
    rows = list(
        await session.scalars(
            select(UniNativeTaskAccount)
            .where(
                UniNativeTaskAccount.is_deleted == 0,
                UniNativeTaskAccount.ocean_project_id.in_((_PULLED_PROJECT, _UNI_PROJECT)),
            )
            .order_by(UniNativeTaskAccount.ocean_project_id.desc(), UniNativeTaskAccount.id)
        )
    )
    advertiser = await _require_advertiser(session, _PULLED_ADVERTISER)
    if not rows:
        await _insert_uni_task(session, advertiser, douyin)
        return
    for row in rows:
        row.ocean_project_id = _UNI_PROJECT
        row.ocean_promotion_id = _UNI_PROMOTION
        if await _uni_douyin_free(session, row, douyin.id):
            row.douyin_account_id = douyin.id
        if await _uni_advertiser_free(session, row, advertiser.id):
            row.advertiser_account_id = advertiser.id
    await session.flush()


async def _uni_douyin_free(session: AsyncSession, row: UniNativeTaskAccount, douyin_id: int) -> bool:
    if row.douyin_account_id == douyin_id:
        return True
    clash = await session.scalar(
        select(UniNativeTaskAccount.id).where(
            UniNativeTaskAccount.task_id == row.task_id,
            UniNativeTaskAccount.douyin_account_id == douyin_id,
            UniNativeTaskAccount.id != row.id,
        )
    )
    return clash is None


async def _uni_advertiser_free(session: AsyncSession, row: UniNativeTaskAccount, advertiser_id: int) -> bool:
    if row.advertiser_account_id == advertiser_id:
        return True
    clash = await session.scalar(
        select(UniNativeTaskAccount.id).where(
            UniNativeTaskAccount.task_id == row.task_id,
            UniNativeTaskAccount.advertiser_account_id == advertiser_id,
            UniNativeTaskAccount.id != row.id,
        )
    )
    return clash is None


async def _insert_uni_task(session: AsyncSession, advertiser: AdvertiserAccount, douyin: DouyinAccount) -> None:
    task = UniNativeTask(
        template_id=10,
        pitcher_user_id=_PITCHER_ID,
        series_id=1,
        project_budget=Decimal("500.00"),
        roi_coefficient=Decimal("1.250"),
        status=NativeTaskStatus.DONE,
        materials_uploaded=True,
        executed_at=beijing_now(),
    )
    session.add(task)
    await session.flush()
    session.add(
        UniNativeTaskAccount(
            task_id=task.id,
            douyin_account_id=douyin.id,
            advertiser_account_id=advertiser.id,
            sort_order=0,
            ocean_project_id=_UNI_PROJECT,
            ocean_promotion_id=_UNI_PROMOTION,
        )
    )
    await session.flush()


async def _ensure_oe_projects(session: AsyncSession, std_douyin: DouyinAccount, uni_douyin: DouyinAccount) -> None:
    """巨量项目和广告。已有项目只纠正主体和广告主，不覆盖名称和预算 JSON。"""
    await _ensure_seed_oe_project(session, std_douyin)
    pulled = await _oe_project(session, _PULLED_PROJECT)
    if pulled is not None:
        pulled.subject_id = await _subject_id(session, 12555)
        pulled.advertiser_id = _PULLED_ADVERTISER
    await _ensure_uni_oe_project(session, uni_douyin)
    await session.flush()


async def _ensure_seed_oe_project(session: AsyncSession, douyin: DouyinAccount) -> None:
    subject_id = await _subject_id(session, 88001)
    project = await _oe_project(session, _SEED_PROJECT)
    if project is None:
        budget = await _seed_project_budget(session)
        session.add(
            OeProject(
                advertiser_id=_SEED_ADVERTISER,
                ocean_project_id=_SEED_PROJECT,
                name="夹具项目8001",
                subject_id=subject_id,
                opt_status="ENABLE",
                template=project_template(budget),
            )
        )
        await session.flush()
        await _ensure_seed_promotions(session, douyin)
        return
    project.subject_id = subject_id
    project.advertiser_id = _SEED_ADVERTISER


async def _seed_project_budget(session: AsyncSession) -> Decimal | None:
    task_project = await session.scalar(
        select(DeliveryTaskProject).where(
            DeliveryTaskProject.ocean_project_id == _SEED_PROJECT,
            DeliveryTaskProject.is_deleted == 0,
        )
    )
    if task_project is None:
        return Decimal("300.00")
    draft = await session.get(DeliveryTaskDraft, task_project.task_id)
    if draft is not None and draft.project_budget is not None:
        return draft.project_budget
    if draft is not None:
        template = await session.get(DeliveryTemplate, draft.template_id)
        if template is not None and template.project_budget is not None:
            return template.project_budget
    return Decimal("300.00")


async def _ensure_seed_promotions(session: AsyncSession, douyin: DouyinAccount) -> None:
    draft = await _seed_draft(session)
    series_id = draft.series_id if draft is not None else 2
    douyin_id = draft.douyin_account_id if draft is not None and draft.douyin_account_id is not None else douyin.id
    ad_budget = draft.ad_budget if draft is not None else Decimal("100.00")
    names = await _promotion_names(session, _SEED_ADVERTISER, _SEED_PROJECT)
    for promotion_id in (8001, 8002):
        if await _promotion_exists(session, _SEED_ADVERTISER, promotion_id):
            continue
        session.add(
            OePromotion(
                advertiser_id=_SEED_ADVERTISER,
                promotion_id=promotion_id,
                ocean_project_id=_SEED_PROJECT,
                series_id=series_id,
                douyin_account_id=douyin_id,
                opt_status="ENABLE",
                name=names.get(promotion_id) or f"夹具广告{promotion_id}",
                budget=ad_budget,
            )
        )


async def _seed_draft(session: AsyncSession) -> DeliveryTaskDraft | None:
    task_project = await session.scalar(
        select(DeliveryTaskProject).where(
            DeliveryTaskProject.ocean_project_id == _SEED_PROJECT,
            DeliveryTaskProject.is_deleted == 0,
        )
    )
    if task_project is None:
        return None
    return await session.get(DeliveryTaskDraft, task_project.task_id)


async def _ensure_uni_oe_project(session: AsyncSession, douyin: DouyinAccount) -> None:
    subject_id = await _subject_id(session, 88002)
    project = await _oe_project(session, _UNI_PROJECT)
    if project is None:
        budget, roi = await _uni_budget(session)
        session.add(
            OeProject(
                advertiser_id=_PULLED_ADVERTISER,
                ocean_project_id=_UNI_PROJECT,
                name=_UNI_PROJECT_NAME,
                subject_id=subject_id,
                opt_status="ENABLE",
                template=project_template(budget, roi),
            )
        )
    else:
        project.subject_id = subject_id
        project.advertiser_id = _PULLED_ADVERTISER
    promotion = await session.scalar(
        select(OePromotion).where(
            OePromotion.advertiser_id == _PULLED_ADVERTISER,
            OePromotion.promotion_id == _UNI_PROMOTION,
        )
    )
    if promotion is None:
        session.add(
            OePromotion(
                advertiser_id=_PULLED_ADVERTISER,
                promotion_id=_UNI_PROMOTION,
                ocean_project_id=_UNI_PROJECT,
                series_id=1,
                douyin_account_id=douyin.id,
                opt_status="ENABLE",
                name=_UNI_PROMOTION_NAME,
            )
        )
        return
    promotion.douyin_account_id = douyin.id


async def _uni_budget(session: AsyncSession) -> tuple[Decimal, Decimal]:
    link = await session.scalar(
        select(UniNativeTaskAccount).where(
            UniNativeTaskAccount.ocean_project_id == _UNI_PROJECT,
            UniNativeTaskAccount.is_deleted == 0,
        )
    )
    if link is None:
        return Decimal("500.00"), Decimal("1.250")
    task = await session.get(UniNativeTask, link.task_id)
    if task is None:
        return Decimal("500.00"), Decimal("1.250")
    return task.project_budget, task.roi_coefficient


async def _oe_project(session: AsyncSession, ocean_project_id: int) -> OeProject | None:
    return await session.scalar(select(OeProject).where(OeProject.ocean_project_id == ocean_project_id))


async def _promotion_exists(session: AsyncSession, advertiser_id: int, promotion_id: int) -> bool:
    found = await session.scalar(
        select(OePromotion.id).where(
            OePromotion.advertiser_id == advertiser_id,
            OePromotion.promotion_id == promotion_id,
        )
    )
    return found is not None


async def _promotion_names(session: AsyncSession, advertiser_id: int, ocean_project_id: int) -> dict[int, str]:
    rows = await session.execute(
        select(OeMaterialReport.cdp_promotion_id, func.max(OeMaterialReport.cdp_promotion_name))
        .where(
            OeMaterialReport.advertiser_id == advertiser_id,
            OeMaterialReport.cdp_project_id == ocean_project_id,
            OeMaterialReport.is_deleted == 0,
        )
        .group_by(OeMaterialReport.cdp_promotion_id)
    )
    return {int(promotion_id): str(name) for promotion_id, name in rows.all() if name}


async def _ensure_hours(session: AsyncSession) -> None:
    """投放小时和素材小时留着。全域小时只把旧项目号改成 80030001，空库才按表插入。"""
    await session.execute(
        update(OeUniProjectReport)
        .where(
            OeUniProjectReport.advertiser_id == _PULLED_ADVERTISER,
            OeUniProjectReport.cdp_project_id == _PULLED_PROJECT,
            OeUniProjectReport.is_deleted == 0,
        )
        .values(cdp_project_id=_UNI_PROJECT)
        .execution_options(synchronize_session=False)
    )
    now = beijing_now()
    for fact in _UNI_HOUR_FACTS:
        hour = fact[0]
        taken = await session.scalar(
            select(OeUniProjectReport.id).where(
                OeUniProjectReport.advertiser_id == _PULLED_ADVERTISER,
                OeUniProjectReport.stat_time_hour == hour,
                OeUniProjectReport.cdp_project_id == _UNI_PROJECT,
            )
        )
        if taken is not None:
            continue
        gmv = Decimal(fact[3])
        session.add(
            OeUniProjectReport(
                advertiser_id=_PULLED_ADVERTISER,
                stat_time_hour=hour,
                cdp_project_id=_UNI_PROJECT,
                cdp_project_name=_UNI_HOUR_NAME,
                all_stat_cost_trend=Decimal(fact[1]),
                all_stat_total_cost_trend=Decimal(fact[2]),
                all_gmv_trend=gmv,
                all_billing_gmv_0day_trend=gmv,
                all_billing_gmv_24h_trend=gmv,
                all_billing_gmv_3days_trend=gmv,
                all_income_trend=Decimal(fact[4]),
                all_income_0day_trend=Decimal(fact[5]),
                all_pay_amount_income_trend=Decimal(fact[6]),
                all_micro_game_income_trend=Decimal(fact[7]),
                all_roi_trend=Decimal("1.2000"),
                all_roi_24h_trend=Decimal("0.8000"),
                all_roi_0day_trend=Decimal("0.9000"),
                all_roi_3days_trend=Decimal("1.1000"),
                all_show_cnt_trend=int(fact[8]),
                all_click_cnt_trend=int(fact[9]),
                synced_at=now,
            )
        )
    await _ensure_uni_material_hours(session)
    await session.flush()


async def _ensure_uni_material_hours(session: AsyncSession) -> None:
    existing = await session.scalar(
        select(OeMaterialReport.id).where(
            OeMaterialReport.advertiser_id == _PULLED_ADVERTISER,
            OeMaterialReport.cdp_project_id == _UNI_PROJECT,
            OeMaterialReport.cdp_promotion_id == _UNI_PROMOTION,
            OeMaterialReport.material_id == _UNI_MATERIAL,
            OeMaterialReport.is_deleted == 0,
        )
    )
    if existing is not None:
        return
    now = beijing_now()
    day = now.astimezone(BEIJING).date().isoformat()
    for row in uni_hour_rows(_PULLED_ADVERTISER, day, now):
        taken = await session.scalar(
            select(OeMaterialReport.id).where(
                OeMaterialReport.advertiser_id == row.advertiser_id,
                OeMaterialReport.stat_time_hour == row.stat_time_hour,
                OeMaterialReport.material_id == row.material_id,
                OeMaterialReport.cdp_promotion_id == row.cdp_promotion_id,
                OeMaterialReport.cdp_project_id == row.cdp_project_id,
            )
        )
        if taken is None:
            session.add(row)


async def _ensure_libraries(session: AsyncSession) -> None:
    """三个商品库。所挂组织还活着就留在原组织，否则挂到未软删的授权组织。"""
    specs = (
        (77001, "测试视频兜底库", "video", "fallback"),
        (77002, "测试视频标准库", "video", "standard"),
        (77003, "测试小说兜底库", "novel", "fallback"),
    )
    for library_no, name, kind, role in specs:
        alive = await session.scalar(
            select(ProductLibrary).where(ProductLibrary.library_no == library_no, ProductLibrary.is_deleted == 0)
        )
        if alive is None:
            placed = await _granted_org(session, _HAOYUN_ORG)
            if placed is None:
                raise RuntimeError(f"没有未软删的授权组织可挂商品库 {library_no}")
            session.add(
                ProductLibrary(
                    name=name,
                    library_no=library_no,
                    library_kind=kind,
                    organization_id=placed[0].id,
                    library_role=role,
                    uploaded_count=0,
                )
            )
            continue
        org = await session.get(OeOrganization, alive.organization_id)
        if org is None or org.is_deleted != 0:
            placed = await _granted_org(session, _HAOYUN_ORG)
            if placed is None:
                raise RuntimeError(f"没有未软删的授权组织可挂商品库 {library_no}")
            alive.organization_id = placed[0].id
        alive.name = name
        alive.library_kind = kind
        alive.library_role = role
    await session.flush()
    video = await session.scalar(
        select(ProductLibrary).where(ProductLibrary.library_no == 77002, ProductLibrary.is_deleted == 0)
    )
    if video is None:
        return
    assigned = await session.scalar(
        select(ProductLibraryPitcher).where(
            ProductLibraryPitcher.user_id == _PITCHER_ID,
            ProductLibraryPitcher.organization_id == video.organization_id,
            ProductLibraryPitcher.library_kind == "video",
        )
    )
    if assigned is not None:
        return
    session.add(
        ProductLibraryPitcher(
            product_library_id=video.id,
            user_id=_PITCHER_ID,
            organization_id=video.organization_id,
            library_kind="video",
        )
    )


async def _ensure_robots(session: AsyncSession) -> None:
    """只补未软删的机器人、全域机器人和自动规则。id 已在不覆盖，已软删不复活。"""
    for row in _standard_robots():
        if await session.get(StandardNativeRobotRule, row["id"]) is not None:
            continue
        session.add(StandardNativeRobotRule(**row))
    for row in _uni_robots():
        if await session.get(UniRobotRule, row["id"]) is not None:
            continue
        session.add(UniRobotRule(**row))
    for row in _auto_rules():
        if await session.get(DeliveryAutoRule, row["id"]) is not None:
            continue
        session.add(DeliveryAutoRule(**row))
    await session.flush()
    for row in _auto_rule_series():
        if await session.get(DeliveryAutoRuleSeries, row["id"]) is not None:
            continue
        pair = await session.scalar(
            select(DeliveryAutoRuleSeries.id).where(
                DeliveryAutoRuleSeries.rule_id == row["rule_id"],
                DeliveryAutoRuleSeries.series_id == row["series_id"],
            )
        )
        if pair is not None:
            continue
        session.add(DeliveryAutoRuleSeries(**row))
    await session.flush()


def _standard_robots() -> list[dict[str, object]]:
    # id, name, charge, kind, schedule, hour, minute, template, pitcher, platform,
    # accounts, videos, stat, cost_min, cost_max, recovery_min, recovery_max, enabled,
    # last_ran_at, end_hour, end_minute, delivery_hours, bid, cycle, sort
    raw = (
        (5, "测试免费漫剧机器人1", "IAA", "nb", "cycle", 18, 0, 5, 4, None, 2, 555, None, "22.00", None, "555.0000", None, True, "2026-10-14 05:00:44.010384+00", 22, 0, 2, "NO_BID", 10, 1),
        (8, "测试免费漫剧机器人3", "IAA", "promotion_link", "cycle", 3, 0, 6, 4, 1, 3, 200, None, None, None, None, None, True, "2026-10-14 05:00:44.010384+00", 20, 59, None, None, 60, 4),
        (11, "测试付费漫剧机器人1", "IAP", "nb", "cycle", 4, 0, 7, 4, None, 1, 333, None, "23.00", None, "44.0000", None, True, "2026-10-14 05:00:44.010384+00", 5, 0, 5, "CUSTOM", 60, 1),
        (16, "测试付费漫剧机器人3", "IAP", "promotion_link", "cycle", 4, 0, 7, 4, 2, 20, 800, None, None, None, None, None, True, "2026-10-14 05:00:44.010384+00", 21, 59, None, None, 10, 4),
        (7, "测试免费漫剧机器人1", "IAA", "nb", "period", 3, 0, 5, 1, None, 3, 200, None, "123.00", None, "345.0000", None, False, None, None, None, None, None, None, 0),
        (10, "联调付费NB-1013-改", "IAP", "nb", "period", 0, 0, 7, 1, None, 3, 200, None, "10.00", None, "20.0000", None, True, "2026-10-14 01:30:54.37307+00", None, None, None, None, None, 0),
        (9, "132123123", "IAA", "nb", "period", 4, 0, 6, 4, None, 3, 200, None, "333.00", None, "555.0000", None, False, None, None, None, None, None, None, 0),
        (6, "测试免费机器人2", "IAA", "drama", "daily", 1, 0, 6, 4, 1, 20, 200, "today", "555.00", None, "111.0000", None, True, "2026-10-14 01:30:54.37307+00", None, None, None, None, None, 6),
        (15, "测试付费漫剧机器人2", "IAP", "drama", "daily", 6, 0, 7, 4, 2, 6, 800, "yesterday", "123.00", None, None, "135.0000", True, "2026-10-14 01:30:54.37307+00", None, None, None, None, None, 5),
        (12, "联调字段回显NB-1013", "IAA", "nb", "cycle", 18, 0, 6, 1, None, 3, 200, None, "22.00", None, "55.0000", None, False, None, 22, 30, 8, "CUSTOM", 30, 7),
        (13, "联调字段回显剧-1013", "IAA", "drama", "daily", 16, 21, 6, 1, 1, 3, 200, "today", "10.00", None, "20.0000", None, False, None, None, None, None, None, None, 5),
        (14, "联调字段回显链-1013", "IAA", "promotion_link", "cycle", 1, 0, 6, 1, 1, 3, 200, None, None, None, None, None, False, None, 10, 0, None, None, 60, 3),
    )
    rows: list[dict[str, object]] = []
    for item in raw:
        rows.append(
            {
                "id": item[0],
                "name": item[1],
                "charge_mode": item[2],
                "rule_kind": item[3],
                "schedule_kind": item[4],
                "schedule_hour": item[5],
                "schedule_minute": item[6],
                "template_id": item[7],
                "pitcher_user_id": item[8],
                "platform_id": item[9],
                "accounts_per_series": item[10],
                "max_videos_per_series": item[11],
                "stat_span": item[12],
                "cost_min": _dec(item[13]),
                "cost_max": _dec(item[14]),
                "recovery_min": _dec(item[15]),
                "recovery_max": _dec(item[16]),
                "is_enabled": item[17],
                "last_ran_at": None if item[18] is None else _ts(item[18]),
                "schedule_end_hour": item[19],
                "schedule_end_minute": item[20],
                "delivery_hours": item[21],
                "bid_type": item[22],
                "cycle_minutes": item[23],
                "sort_order": item[24],
            }
        )
    return rows


def _uni_robots() -> list[dict[str, object]]:
    raw = (
        (4, "drama_condition", "联调全域剧条件-1013", 15, 1, 800, 15, 59, False, "today", "10.00", "100.00", "20.0000", "80.0000", 1, "daily", 0, None, None, None),
        (7, "drama_condition", "测试规则3", 10, 1, 200, 5, 0, True, "today", "2.00", "345345.00", "5.0000", "454.0000", 4, "daily", 0, None, None, None),
        (8, "drama_condition", "测试规则4", 12, 1, 800, 6, 0, True, "yesterday", "4.00", "345.00", "56.0000", "242.0000", 4, "daily", 0, None, None, None),
        (10, "drama_condition", "联调全域排序剧-1013", 15, 1, 800, 16, 52, True, "today", "1.00", "10.00", "2.0000", "20.0000", 1, "daily", 4, None, None, None),
        (5, "promotion_link", "测试漫剧机器人规则1", 15, 1, 300, 4, 0, True, None, None, None, None, None, 4, "daily", 9, None, None, None),
        (11, "promotion_link", "联调全域窗口-1013", 15, 1, 800, 2, 0, False, None, None, None, None, None, 1, "cycle", 6, 30, 11, 0),
        (6, "promotion_link", "测试漫剧机器人规则2", 12, 1, 500, 2, 0, False, None, None, None, None, None, 4, "cycle", 4, 60, 6, 0),
    )
    return [
        {
            "id": item[0],
            "rule_kind": item[1],
            "name": item[2],
            "template_id": item[3],
            "platform_id": item[4],
            "max_videos_per_series": item[5],
            "schedule_hour": item[6],
            "schedule_minute": item[7],
            "is_enabled": item[8],
            "stat_span": item[9],
            "cost_min": _dec(item[10]),
            "cost_max": _dec(item[11]),
            "recovery_min": _dec(item[12]),
            "recovery_max": _dec(item[13]),
            "pitcher_user_id": item[14],
            "schedule_kind": item[15],
            "sort_order": item[16],
            "cycle_minutes": item[17],
            "schedule_end_hour": item[18],
            "schedule_end_minute": item[19],
        }
        for item in raw
    ]


def _auto_rules() -> list[dict[str, object]]:
    return [
        {
            "id": 2,
            "name": "IAA端原生短剧消耗自动批量-2026-10-09-14:48",
            "charge_mode": "IAA",
            "template_id": 5,
            "pitcher_user_id": 1,
            "accounts_per_series": 2,
            "max_videos_per_series": 200,
            "schedule_start": None,
            "schedule_end": None,
            "cost_min": Decimal("0.00"),
            "cost_max": Decimal("5.00"),
            "roi_min": Decimal("0.0000"),
            "roi_max": Decimal("87.0000"),
            "publish_start": None,
            "publish_end": None,
            "no_bid_only": False,
            "is_enabled": True,
            "ran_at": _ts("2026-10-09 08:30:07.795088+00"),
            "rule_kind": "publish",
            "theater": "番茄漫剧",
        },
        {
            "id": 3,
            "name": "IAP端原生短剧消耗自动批量-2026-10-09-17:01",
            "charge_mode": "IAP",
            "template_id": 7,
            "pitcher_user_id": 1,
            "accounts_per_series": 3,
            "max_videos_per_series": 200,
            "schedule_start": None,
            "schedule_end": None,
            "cost_min": Decimal("0.00"),
            "cost_max": Decimal("3.00"),
            "roi_min": Decimal("0.0000"),
            "roi_max": Decimal("4.0000"),
            "publish_start": None,
            "publish_end": None,
            "no_bid_only": False,
            "is_enabled": True,
            "ran_at": _ts("2026-10-09 09:01:55.714555+00"),
            "rule_kind": "publish",
            "theater": "番茄漫剧",
        },
        {
            "id": 4,
            "name": "IAA端原生自动批量-2026-10-09-17:02",
            "charge_mode": "IAA",
            "template_id": 6,
            "pitcher_user_id": 1,
            "accounts_per_series": 1,
            "max_videos_per_series": 200,
            "schedule_start": _ts("2026-10-08 16:00:00+00"),
            "schedule_end": _ts("2026-10-08 16:00:00+00"),
            "cost_min": Decimal("0.00"),
            "cost_max": Decimal("56.00"),
            "roi_min": None,
            "roi_max": None,
            "publish_start": date(2026, 10, 9),
            "publish_end": date(2026, 10, 9),
            "no_bid_only": False,
            "is_enabled": True,
            "ran_at": _ts("2026-10-09 09:02:34.633076+00"),
            "rule_kind": "publish",
            "theater": "番茄漫剧",
        },
    ]


def _auto_rule_series() -> list[dict[str, int]]:
    return [
        {"id": 2, "rule_id": 2, "series_id": 3, "sort_order": 0},
        {"id": 3, "rule_id": 2, "series_id": 1, "sort_order": 1},
        {"id": 4, "rule_id": 3, "series_id": 5, "sort_order": 0},
        {"id": 5, "rule_id": 4, "series_id": 1, "sort_order": 0},
    ]


async def _ensure_materials(session: AsyncSession) -> None:
    """没有未删的「夹具视频」就插一条并分给用户 3。没有「夹具标题」就插一条。"""
    video = await session.scalar(
        select(MaterialVideo).where(MaterialVideo.name == "夹具视频", MaterialVideo.is_deleted == 0)
    )
    if video is None:
        tag = await session.scalar(
            select(MaterialVideoTag).where(MaterialVideoTag.name == "夹具视频", MaterialVideoTag.is_deleted == 0)
        )
        if tag is None:
            occupied = await session.scalar(select(MaterialVideoTag).where(MaterialVideoTag.name == "夹具视频"))
            if occupied is None:
                tag = MaterialVideoTag(name="夹具视频")
                session.add(tag)
                await session.flush()
            else:
                tag = occupied
        video = MaterialVideo(
            name="夹具视频",
            material_type=MaterialType.VERTICAL_VIDEO,
            file_urls=["https://example.com/fixture/clip.mp4"],
            series_id=1,
            platform=Platform.TOMATO,
            tag_id=tag.id,
            ownership=Ownership.PRIVATE,
            uploader_id=_PITCHER_ID,
        )
        session.add(video)
        await session.flush()
    pitcher = await session.scalar(
        select(MaterialVideoPitcher).where(
            MaterialVideoPitcher.video_id == video.id,
            MaterialVideoPitcher.operator_id == _PITCHER_ID,
            MaterialVideoPitcher.user_id == _PITCHER_ID,
        )
    )
    if pitcher is None:
        session.add(MaterialVideoPitcher(video_id=video.id, operator_id=_PITCHER_ID, user_id=_PITCHER_ID))
    title = await session.scalar(select(MaterialTitle.id).where(MaterialTitle.title == "夹具标题", MaterialTitle.is_deleted == 0))
    if title is None:
        session.add(MaterialTitle(title="夹具标题", category=TitleCategory.COMMON, uploader_id=_PITCHER_ID))
    await session.flush()


async def _advance_sequences(session: AsyncSession) -> None:
    """显式主键插完后，把身份序列拨到当前最大 id，避免下次自增撞上。"""
    for table in _ID_TABLES:
        seq = await session.scalar(text(f"SELECT pg_get_serial_sequence('{table}', 'id')"))
        if not seq:
            continue
        max_id = await session.scalar(text(f"SELECT MAX(id) FROM {table}"))
        if max_id is None:
            continue
        await session.execute(
            text("SELECT setval(CAST(:seq AS regclass), :max_id)"),
            {"seq": seq, "max_id": max_id},
        )


async def _ensure_profit(session: AsyncSession) -> None:
    """日表刷新之后按唯一键纠正 10 行利润。已有只改消耗和回收。"""
    for stat_date, charge_mode, stat_cost, recovery in _PROFIT_ROWS:
        row = await session.scalar(
            select(ReportProfitDay).where(
                ReportProfitDay.stat_date == stat_date,
                ReportProfitDay.scope == "standard",
                ReportProfitDay.charge_mode == charge_mode,
                ReportProfitDay.drama_type == "",
                ReportProfitDay.platform == "tomato",
                ReportProfitDay.department_id == 2,
                ReportProfitDay.pitcher_id == _PITCHER_ID,
            )
        )
        if row is None:
            session.add(
                ReportProfitDay(
                    stat_date=stat_date,
                    scope="standard",
                    charge_mode=charge_mode,
                    drama_type="",
                    platform="tomato",
                    department_id=2,
                    department_name="投放一部",
                    pitcher_id=_PITCHER_ID,
                    pitcher_name="短剧投手",
                    stat_cost=stat_cost,
                    recovery=recovery,
                )
            )
            continue
        row.stat_cost = stat_cost
        row.recovery = recovery
        if row.is_deleted:
            row.is_deleted = 0
            row.deleted_at = None


async def _ensure_roi(session: AsyncSession) -> None:
    start = date(2026, 10, 1)
    end = date(2026, 10, 31)
    rows = list(
        await session.scalars(
            select(ReportRoiConfig).where(
                ReportRoiConfig.date_start == start,
                ReportRoiConfig.date_end == end,
                ReportRoiConfig.is_deleted == 0,
            )
        )
    )
    if not rows:
        session.add(ReportRoiConfig(date_start=start, date_end=end, roi_rate=Decimal("1.05")))
        return
    for row in rows:
        row.roi_rate = Decimal("1.05")
