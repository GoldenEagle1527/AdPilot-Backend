"""素材报表只收巨量直接返回的字段，公式列不建，假令牌不拉。"""

from __future__ import annotations

import asyncio
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from app.modules.account.model import OeMaterialReport
from app.modules.oceanengine.material_report import (
    dimensions_for,
    pair_report_reads,
    report_days,
    row_from_report,
    run_hourly_material_report,
    usable_access_token,
)

_FORMULA_COLUMNS = {
    "ctr",
    "cpm_platform",
    "cpc_platform",
    "conversion_cost",
    "conversion_rate",
    "active_cost",
    "active_arpu",
    "recycle_rate",
    "pay_amount_roi",
    "attribution_billing_game_in_app_roi_1day",
    "attribution_micro_game_0d_roi",
    "profit",
    "group_avg_roi",
}


class MaterialReportShapeTests(unittest.TestCase):
    def test_formula_columns_are_absent(self) -> None:
        names = set(OeMaterialReport.__table__.columns.keys())
        self.assertTrue(_FORMULA_COLUMNS.isdisjoint(names))
        for name in (
            "advertiser_id",
            "stat_time_hour",
            "material_id",
            "ad_platform_material_name",
            "cdp_promotion_id",
            "cdp_promotion_name",
            "cdp_project_id",
            "cdp_project_name",
            "stat_cost",
            "attribution_billing_game_in_app_ltv_1day",
            "stat_pay_amount",
            "show_cnt",
            "click_cnt",
            "convert_cnt",
            "active",
            "game_addiction",
        ):
            self.assertIn(name, names)

    def test_hour_grain_is_only_the_latest_eight_days(self) -> None:
        today = date(2026, 10, 10)
        self.assertEqual(dimensions_for(today, today)[0], "stat_time_hour")
        self.assertEqual(dimensions_for(date(2026, 10, 3), today)[0], "stat_time_hour")
        self.assertEqual(dimensions_for(date(2026, 10, 2), today)[0], "stat_time_day")

    def test_report_days_cover_thirty_dates(self) -> None:
        days = report_days(datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc))
        self.assertEqual(len(days), 30)
        self.assertEqual(days[-1].isoformat(), "2026-10-10")
        self.assertEqual(days[0].isoformat(), "2026-09-11")

    def test_mock_and_expired_tokens_are_unusable(self) -> None:
        now = datetime(2026, 10, 10, tzinfo=timezone.utc)
        self.assertIsNone(usable_access_token(None, None, now))
        self.assertIsNone(usable_access_token("mock-access-token", None, now))
        self.assertIsNone(usable_access_token("real-token", datetime(2026, 10, 9, tzinfo=timezone.utc), now))
        self.assertEqual(usable_access_token("real-token", datetime(2026, 10, 11, tzinfo=timezone.utc), now), "real-token")

    def test_single_live_token_only_backs_real_advertiser_ids(self) -> None:
        pairs = pair_report_reads(
            [(9001001001, 3), (1873916032590219, 1)],
            {4: "live-token"},
        )
        self.assertEqual(pairs, [(1873916032590219, "live-token")])

    def test_hourly_pull_does_not_run_while_mock(self) -> None:
        settings = Mock()
        settings.oceanengine.mock = True
        with patch("app.modules.oceanengine.material_report.get_settings", return_value=settings):
            written = asyncio.run(run_hourly_material_report(object()))
        self.assertEqual(written, 0)

    def test_process_starts_hourly_material_report_only_when_mock_is_off(self) -> None:
        main = (Path(__file__).resolve().parents[3] / "main.py").read_text(encoding="utf-8")
        self.assertIn("_material_report_loop", main)
        self.assertIn("if not settings.oceanengine.mock:", main)
        self.assertIn("_MATERIAL_REPORT_INTERVAL_SECONDS = 3600", main)

    def test_canned_snapshot_row_is_not_a_material_row(self) -> None:
        """假客户端的广告快照没有素材主键，不能写进新表。"""
        row = row_from_report(
            {"promotion_id": 8001, "stat_cost": 120.0, "attribution_micro_game_0d_roi": 0.3},
            1873916032590219,
            datetime(2026, 10, 10, tzinfo=timezone.utc),
        )
        self.assertIsNone(row)
