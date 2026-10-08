"""手动补前端演示数据。启动不会 import，也不会自动执行。

在 backend/ 下：python scripts/ensure_frontend_demo.py
库里还没有指定应用或授权组织时直接抛错。
"""

from __future__ import annotations

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import dispose_engine, get_session, init_engine
from app.core.times import beijing_now
from app.modules.account.model import (
    AdvertiserAccount,
    DeliverySubject,
    DouyinAccount,
    DouyinPitcher,
    OeApp,
    OeOrganization,
    ProductLibrary,
    ProductLibraryPitcher,
)
from app.modules.system_admin.domain.models import UserTag, UserTagLink

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


async def _main() -> None:
    init_engine(get_settings())
    try:
        async for session in get_session():
            await ensure_frontend_demo(session)
            await session.commit()
            return
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(_main())
