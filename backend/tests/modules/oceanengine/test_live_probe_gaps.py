"""用真实探测夹具对照当前巨量模块。不访问开放平台。"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from datetime import datetime, timedelta, timezone

from app.modules.oceanengine.catalog import organization_token_valid
from app.modules.oceanengine.delivery import _project_remote_body
from app.modules.oceanengine.runtime import _page_count, token_needs_refresh
from app.modules.oceanengine.schema import ProjectCreate
from app.modules.oceanengine.sync import (
    _account_row,
    _organization_identity,
    accounts_from_download,
    list_exceeds_cap,
)

_PROBE = Path(__file__).resolve().parent / "fixtures" / "live_delivery_probe.json"
_SNAPSHOT = Path(__file__).resolve().parent / "fixtures" / "account_snapshot.json"


class LiveProbeGapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.probe = json.loads(_PROBE.read_text(encoding="utf-8"))
        cls.snapshot = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))

    def test_authorized_org_maps_into_organization_row(self) -> None:
        """深圳发行中心这条授权账户能落成组织。"""
        account = self.snapshot["authorized_accounts"][0]
        identity = _organization_identity(
            {
                "account_id": account["advertiser_id"],
                "account_name": account["advertiser_name"],
                "account_role": account["account_role"],
                "account_type": account["account_role"],
            }
        )
        self.assertEqual(identity, (1872115109920903, "深圳发行中心", "PLATFORM_ROLE_ENTERPRISE_BP_ADMIN"))

    def test_advertiser_row_maps(self) -> None:
        """广告主名单上的 id、名称能收成同步用的行。"""
        row = self.snapshot["advertisers"][0]
        self.assertEqual(
            _account_row(
                {
                    "account_id": row["account_id"],
                    "account_name": row["account_name"],
                    "account_type": row["account_type"],
                }
            ),
            {
                "account_id": row["account_id"],
                "account_name": row["account_name"],
            },
        )

    def test_direct_list_page_count_walks_past_the_api_cap(self) -> None:
        """直挂名单的 total_page 是 231。超过 1 万条时同步改走导出，不再按这个页数翻完。"""
        page_info = self.probe["ebp_direct"]["page_info"]
        self.assertEqual(_page_count({"page_info": page_info}, 100), 231)
        self.assertGreater(page_info["total_number"], 10_000)
        self.assertLess(self.probe["ebp_direct"]["total_number"], self.probe["ebp_traverse"]["total_number"])

    def test_create_project_drops_fields_present_on_the_live_project(self) -> None:
        """真实项目上的优化目标、商品、定向和抖音号推广会进入提交体。"""
        scalars = self.probe["project_scalars"]
        remote = _project_remote_body(
            ProjectCreate(
                advertiser_id=scalars["advertiser_id"],
                name=scalars["name"],
                landing_type=scalars["landing_type"],
                marketing_goal=scalars["marketing_goal"],
                ad_type=scalars["ad_type"],
                delivery_mode=scalars["delivery_mode"],
                subject_id=1,
                template={
                    "delivery_range": {"inventory_catalog": "UNIVERSAL_SMART"},
                    "delivery_setting": {"budget_mode": "BUDGET_MODE_DAY", "budget": 300},
                    "optimize_goal": {"external_action": "AD_CONVERT_TYPE_ACTIVE"},
                    "related_product": {"product_setting": "SINGLE"},
                    "audience": {"district": "NONE"},
                    "micro_promotion_type": scalars["micro_promotion_type"],
                },
            )
        )
        self.assertEqual(
            set(remote),
            {
                "advertiser_id",
                "name",
                "landing_type",
                "marketing_goal",
                "ad_type",
                "delivery_mode",
                "delivery_range",
                "delivery_setting",
                "optimize_goal",
                "related_product",
                "audience",
                "micro_promotion_type",
            },
        )
        self.assertEqual(remote["micro_promotion_type"], "AWEME")
        self.assertEqual(remote["optimize_goal"]["external_action"], "AD_CONVERT_TYPE_ACTIVE")
        self.assertIn("related_product", remote)
        self.assertIn("audience", remote)

    def test_direct_list_over_cap_is_not_paged_as_complete(self) -> None:
        """直挂 23004 户超过 1 万条，不能当成已经拉全。"""
        page_info = self.probe["ebp_direct"]["page_info"]
        self.assertTrue(list_exceeds_cap({"page_info": page_info}, 100))
        self.assertFalse(
            list_exceeds_cap(
                {"page_info": {"total_number": 10000, "total_page": 100, "page_size": 100}},
                100,
            )
        )

    def test_download_payload_maps_account_rows(self) -> None:
        """导出文件里的账户行与实时列表用同一套 id、名称。"""
        rows = accounts_from_download(
            {
                "data": {
                    "account_list": [
                        {"account_id": 1877302917159945, "account_name": "番茄漫剧", "account_type": "AD_NORMAL"}
                    ]
                }
            }
        )
        self.assertEqual(rows, [{"account_id": 1877302917159945, "account_name": "番茄漫剧"}])

    def test_token_refreshes_inside_five_minutes(self) -> None:
        """访问令牌 5 分钟内过期就续期。没有过期时间的旧票不主动换。"""
        now = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
        self.assertTrue(
            token_needs_refresh(
                access_token="access",
                refresh_token="refresh",
                access_expire_at=now + timedelta(minutes=4),
                now=now,
            )
        )
        self.assertFalse(
            token_needs_refresh(
                access_token="access",
                refresh_token="refresh",
                access_expire_at=now + timedelta(hours=2),
                now=now,
            )
        )
        self.assertFalse(
            token_needs_refresh(
                access_token="access",
                refresh_token="refresh",
                access_expire_at=None,
                now=now,
            )
        )

    def test_organization_token_invalid_after_refresh_failure(self) -> None:
        """刷新失败或已过期时 token_valid 为 false。有票且未过期则为 true。"""
        now = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
        self.assertFalse(
            organization_token_valid(
                access_token="access",
                last_error="刷新失败",
                access_expire_at=now + timedelta(hours=1),
                now=now,
            )
        )
        self.assertFalse(
            organization_token_valid(
                access_token="access",
                last_error=None,
                access_expire_at=now - timedelta(seconds=1),
                now=now,
            )
        )
        self.assertTrue(
            organization_token_valid(
                access_token="access",
                last_error=None,
                access_expire_at=now + timedelta(hours=1),
                now=now,
            )
        )
