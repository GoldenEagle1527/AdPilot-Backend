"""巨量广告联调数据：模板和小时行仍在 mock_seed；mock 启动只调联合夹具一次。"""

from __future__ import annotations

import unittest
from decimal import Decimal
from datetime import datetime
from pathlib import Path

from app.modules.ocean_ads.mock_seed import project_template, uni_hour_rows
from app.modules.ocean_ads.pages import _budget, _stored_roi


def _backend() -> Path:
    return Path(__file__).resolve().parents[3]


class ProjectTemplateTest(unittest.TestCase):
    def test_list_reads_budget_and_roi_back(self) -> None:
        template = project_template(Decimal("500.00"), Decimal("1.250"))
        self.assertEqual(_budget(template), "500.00")
        self.assertEqual(_stored_roi(template), "1.25")

    def test_standard_has_no_roi(self) -> None:
        template = project_template(Decimal("800.00"))
        self.assertEqual(_budget(template), "800.00")
        self.assertEqual(_stored_roi(template), "-")

    def test_missing_budget_shows_empty(self) -> None:
        self.assertIsNone(_budget(project_template(None)))


class UniHourRowsTest(unittest.TestCase):
    def test_two_hours_under_the_uni_project(self) -> None:
        rows = uni_hour_rows(1877368580368602, "2026-10-14", datetime(2026, 10, 14, 12, 0))
        self.assertEqual([row.stat_time_hour for row in rows], ["2026-10-14 10:00:00", "2026-10-14 14:00:00"])
        self.assertEqual({row.cdp_project_id for row in rows}, {80030001})
        self.assertEqual({row.cdp_promotion_id for row in rows}, {80030002})
        self.assertEqual(sum(row.stat_cost for row in rows), Decimal("240.00"))


_RETIRED_SEED_NAMES = (
    "_seed_ocean_ads",
    "_seed_oceanengine",
    "ensure_oceanengine_seed",
    "ensure_report_mock",
    "ensure_ocean_ads_mock",
    "ensure_theater_platforms",
)


class SeedPlacementTest(unittest.TestCase):
    def test_mock_branch_calls_joint_mock_once(self) -> None:
        main = (_backend() / "main.py").read_text(encoding="utf-8")
        mock_branch = main.split("if settings.oceanengine.mock:", 1)[1].split("await _rebuild_report_days()", 1)[0]
        self.assertEqual(mock_branch.count("ensure_joint_mock("), 1)
        for name in _RETIRED_SEED_NAMES:
            self.assertNotIn(name, mock_branch)
