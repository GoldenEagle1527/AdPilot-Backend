"""报表小时快照：广告 BASIC_DATA 与全域 UNI_PROJECT_DATA 的拉取和落库字段。"""

from __future__ import annotations

import asyncio
import json
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import Mock, patch

from app.core.times import BEIJING
from app.modules.account.model import OeDeliveryReport, OeUniProjectReport
from app.modules.oceanengine import delivery_report
from app.modules.oceanengine.delivery_report import (
    BASIC_TOPIC,
    UNI_TOPIC,
    basic_row,
    pull_days,
    report_params,
    run_hourly_delivery_report,
    uni_row,
)

SYNCED = datetime(2026, 10, 13, 10, 0, tzinfo=BEIJING)

_UNI_FIELDS = (
    "all_stat_cost_trend",
    "all_roi_24h_trend",
    "all_stat_total_cost_trend",
    "all_gmv_trend",
    "all_billing_gmv_0day_trend",
    "all_billing_gmv_24h_trend",
    "all_roi_trend",
    "all_roi_0day_trend",
    "all_roi_3days_trend",
    "all_income_trend",
    "all_income_0day_trend",
    "all_pay_amount_income_trend",
    "all_micro_game_income_trend",
)


class SnapshotShapeTests(unittest.TestCase):
    def test_delivery_table_keeps_hour_grain_and_summable_metrics_only(self) -> None:
        names = set(OeDeliveryReport.__table__.columns.keys())
        for name in (
            "stat_time_hour",
            "cdp_project_id",
            "cdp_promotion_id",
            "stat_cost",
            "stat_pay_amount",
            "show_cnt",
            "click_cnt",
            "convert_cnt",
            "active",
            "attribution_game_in_app_ltv_1day",
            "attribution_game_in_app_ltv_8days",
            "attribution_micro_game_0d_ltv",
            "attribution_micro_game_7d_ltv",
        ):
            self.assertIn(name, names)
        self.assertTrue({"ctr", "cpm_platform", "attribution_game_in_app_roi_1day"}.isdisjoint(names))

    def test_uni_table_has_every_field_the_uni_sheets_map(self) -> None:
        names = set(OeUniProjectReport.__table__.columns.keys())
        for name in (*_UNI_FIELDS, "stat_time_hour", "cdp_project_id", "all_billing_gmv_3days_trend"):
            self.assertIn(name, names)

    def test_pull_covers_eight_days_ending_today(self) -> None:
        days = pull_days(datetime(2026, 10, 13, 2, 0, tzinfo=timezone.utc))
        self.assertEqual(len(days), 8)
        self.assertEqual(days[-1], date(2026, 10, 13))
        self.assertEqual(days[0], date(2026, 10, 6))


class RowParseTests(unittest.TestCase):
    def test_basic_row_reads_dimensions_and_metrics(self) -> None:
        raw = {
            "dimensions": {
                "stat_time_hour": "2026-10-13 09:00:00",
                "cdp_project_id": "7679270188483330111",
                "cdp_project_name": "霸总NB",
                "cdp_promotion_id": "7679270259296239657",
                "cdp_promotion_name": "广告一",
            },
            "metrics": {"stat_cost": "12.345", "stat_pay_amount": "3.1", "show_cnt": "100", "active": "-"},
        }
        row = basic_row(raw, 1873916032590219, SYNCED)
        assert row is not None
        self.assertEqual(row["stat_time_hour"], "2026-10-13 09:00:00")
        self.assertEqual(row["cdp_promotion_id"], 7679270259296239657)
        self.assertEqual(row["stat_cost"], Decimal("12.34"))
        self.assertEqual(row["stat_pay_amount"], Decimal("3.10"))
        self.assertEqual(row["show_cnt"], 100)
        self.assertEqual(row["active"], 0)

    def test_basic_row_without_promotion_is_dropped(self) -> None:
        raw = {"dimensions": {"stat_time_hour": "2026-10-13 09:00:00", "cdp_project_id": "1"}}
        self.assertIsNone(basic_row(raw, 1, SYNCED))

    def test_uni_row_keeps_money_ratio_and_counts(self) -> None:
        raw = {
            "dimensions": {"stat_time_hour": "2026-10-13 09:00:00", "cdp_project_id": "42"},
            "metrics": {
                "all_stat_cost_trend": "50.5",
                "all_gmv_trend": "80",
                "all_roi_trend": "1.5842",
                "all_show_cnt_trend": "900",
            },
        }
        row = uni_row(raw, 1, SYNCED)
        assert row is not None
        self.assertEqual(row["all_stat_cost_trend"], Decimal("50.50"))
        self.assertEqual(row["all_roi_trend"], Decimal("1.5842"))
        self.assertEqual(row["all_show_cnt_trend"], 900)
        self.assertEqual(row["all_income_trend"], Decimal("0.00"))

    def test_params_ask_hour_grain_for_the_topic(self) -> None:
        params = report_params(1, UNI_TOPIC, date(2026, 10, 13), 2, ["stat_time_hour", "cdp_project_id"], ["all_stat_cost_trend"])
        self.assertEqual(params["data_topic"], UNI_TOPIC)
        self.assertEqual(json.loads(params["dimensions"])[0], "stat_time_hour")
        self.assertEqual(params["start_time"], "2026-10-13 00:00:00")
        self.assertEqual(params["page"], 2)


class _Client:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def custom_report(self, _token: str, params: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(params)
        if params["data_topic"] != BASIC_TOPIC or params["start_time"] != "2026-10-13 00:00:00":
            return {"data": {"rows": []}}
        return {
            "data": {
                "rows": [
                    {
                        "dimensions": {
                            "stat_time_hour": "2026-10-13 09:00:00",
                            "cdp_project_id": "11",
                            "cdp_promotion_id": "22",
                        },
                        "metrics": {"stat_cost": "5"},
                    }
                ],
                "page_info": {"total_page": 1},
            }
        }


class _Session:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class PullTests(unittest.TestCase):
    def test_hourly_pull_does_not_run_while_mock(self) -> None:
        settings = Mock()
        settings.oceanengine.mock = True
        with patch("app.modules.oceanengine.delivery_report.get_settings", return_value=settings):
            self.assertEqual(asyncio.run(run_hourly_delivery_report(object())), 0)

    def test_pull_topic_upserts_parsed_rows(self) -> None:
        client = _Client()
        session = _Session()
        written: list[dict[str, Any]] = []

        async def upsert(_session: Any, rows: list[dict[str, Any]]) -> None:
            written.extend(rows)

        with (
            patch.object(delivery_report, "beijing_now", return_value=SYNCED),
            patch.object(delivery_report, "_REQUEST_PAUSE_SECONDS", 0),
        ):
            count = asyncio.run(
                delivery_report._pull_topic(
                    session, client, 1, "token", BASIC_TOPIC, delivery_report.BASIC_DIMENSIONS,
                    ["stat_cost"], basic_row, upsert,
                )
            )
        self.assertEqual(count, 1)
        self.assertEqual(len(client.calls), 8)
        self.assertEqual(written[0]["cdp_promotion_id"], 22)
        self.assertEqual(session.commits, 1)

    def test_hourly_loop_also_pulls_delivery_report(self) -> None:
        from pathlib import Path

        main = (Path(__file__).resolve().parents[3] / "main.py").read_text(encoding="utf-8")
        self.assertIn("run_hourly_delivery_report", main)


if __name__ == "__main__":
    unittest.main()
