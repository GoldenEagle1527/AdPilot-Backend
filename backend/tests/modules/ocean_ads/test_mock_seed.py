"""巨量广告联调数据：只在 mock 启动时写，已有同号就不再写。"""

from __future__ import annotations

import unittest
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from app.modules.ocean_ads.mock_seed import ensure_ocean_ads_mock, project_template, uni_hour_rows
from app.modules.ocean_ads.pages import _budget, _stored_roi


def _backend() -> Path:
    return Path(__file__).resolve().parents[3]


class _ExistingRows:
    """库里已有同号的项目。"""

    def __init__(self) -> None:
        self.added: list[object] = []
        self.flushed = False

    async def scalar(self, _statement: object) -> object:
        return SimpleNamespace(id=1, advertiser_id=1877368580368602)

    async def execute(self, _statement: object) -> object:
        raise AssertionError("已有项目时不再读夹具")

    def add(self, row: object) -> None:
        self.added.append(row)

    async def flush(self) -> None:
        self.flushed = True


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


class SeedRunsOnceTest(unittest.IsolatedAsyncioTestCase):
    async def test_existing_projects_are_left_alone(self) -> None:
        session = _ExistingRows()
        await ensure_ocean_ads_mock(session)  # type: ignore[arg-type]
        self.assertEqual(session.added, [])
        self.assertTrue(session.flushed)


class SeedPlacementTest(unittest.TestCase):
    def test_only_startup_calls_the_seed(self) -> None:
        hits: list[str] = []
        for path in (_backend() / "app").rglob("*.py"):
            if "ensure_ocean_ads_mock(" in path.read_text(encoding="utf-8"):
                hits.append(path.relative_to(_backend()).as_posix())
        main = (_backend() / "main.py").read_text(encoding="utf-8")
        self.assertEqual(hits, ["app/modules/ocean_ads/mock_seed.py"])
        self.assertIn("ensure_ocean_ads_mock(session)", main)
        mock_branch = main.split("if settings.oceanengine.mock:", 1)[1].split("await _rebuild_report_days()", 1)[0]
        self.assertIn("await _seed_ocean_ads()", mock_branch)
