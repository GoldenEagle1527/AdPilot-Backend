"""城市分级种子：北京是一线，成都是新一线，编码不重复。"""

from __future__ import annotations

import unittest
from collections import Counter
from pathlib import Path

from app.modules.city_tier.catalog import CITY_TIERS, TIER_ORDER
from app.modules.city_tier.model import OceanCityTier
from app.modules.city_tier.service import group_city_tiers

MIGRATION = Path(__file__).resolve().parents[3] / "alembic" / "versions" / "20261012_05_ocean_city_tier.py"


class CatalogTests(unittest.TestCase):
    def test_known_cities_keep_the_baike_tier_and_ocean_code(self) -> None:
        """北京、上海是一线。成都、佛山是新一线。无锡是二线。"""
        by_name = {name: (tier, code) for tier, code, name, _province, _order in CITY_TIERS}
        self.assertEqual(by_name["北京"], ("一线", "110000"))
        self.assertEqual(by_name["上海"], ("一线", "310000"))
        self.assertEqual(by_name["广州"], ("一线", "440100"))
        self.assertEqual(by_name["深圳"], ("一线", "440300"))
        self.assertEqual(by_name["成都"], ("新一线", "510100"))
        self.assertEqual(by_name["佛山"], ("新一线", "440600"))
        self.assertEqual(by_name["无锡"], ("二线", "320200"))
        self.assertEqual(by_name["海南州"], ("五线", "632500"))

    def test_codes_are_unique_and_counts_match_the_page(self) -> None:
        """四级数量与百科正文一致，编码不重复。"""
        codes = [code for _tier, code, _name, _province, _order in CITY_TIERS]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertEqual(
            Counter(tier for tier, *_rest in CITY_TIERS),
            {"一线": 4, "新一线": 15, "二线": 30, "三线": 70, "四线": 90, "五线": 120},
        )
        self.assertEqual(TIER_ORDER, ("一线", "新一线", "二线", "三线", "四线", "五线"))

    def test_group_keeps_tier_order(self) -> None:
        """分组按一线到五线，组内按名单顺序。"""
        rows = [
            _row("五线", "460300", "三沙", 2),
            _row("一线", "110000", "北京", 1),
            _row("一线", "310000", "上海", 0),
        ]
        grouped = group_city_tiers(rows)
        self.assertEqual([item["tier"] for item in grouped["items"]], list(TIER_ORDER))
        self.assertEqual(
            grouped["items"][0]["cities"],
            [{"ocean_code": "310000", "name": "上海"}, {"ocean_code": "110000", "name": "北京"}],
        )
        self.assertEqual(grouped["items"][-1]["cities"], [{"ocean_code": "460300", "name": "三沙"}])

    def test_migration_follows_the_link_tier_revision(self) -> None:
        """分级表接在推广链档位名那条迁移后面。"""
        text = MIGRATION.read_text(encoding="utf-8")
        self.assertIn('down_revision: Union[str, None] = "20261012_04"', text)
        self.assertIn("ocean_city_tier", text)
        self.assertIn("CITY_TIERS", text)


def _row(tier: str, code: str, name: str, order: int) -> OceanCityTier:
    """造一条未入库的分级行。"""
    row = OceanCityTier(ocean_code=code, name=name, province_name="", tier=tier, sort_order=order)
    return row
