"""利润和素材报表的口径：ROI 重叠、盈亏按天、nobid、新剧、素材手权限。"""

from __future__ import annotations

import unittest
from datetime import date, datetime
from decimal import Decimal

from app.core.times import BEIJING
from app.modules.report.ledger import (
    library_ids,
    MaterialSlice,
    ProjectCard,
    RawMaterial,
    RoiSpan,
    SeriesCard,
    VideoCard,
    build_slices,
    drama_band,
    drama_editor_table,
    editor_only,
    editor_spend_table,
    editor_stat_table,
    group_avg_roi,
    is_nobid,
    locked_pitcher,
    material_detail_table,
    narrow_departments,
    nb_table,
    profit_table,
    profit_visible,
    roi_for,
)

DAY = date(2026, 10, 13)
NEXT = date(2026, 10, 14)


def span(config_id: int, start: date, end: date, rate: str, hour: int) -> RoiSpan:
    return RoiSpan(config_id, start, end, Decimal(rate), datetime(2026, 10, 1, hour, tzinfo=BEIJING))


def project(**kwargs: object) -> ProjectCard:
    values: dict[str, object] = {
        "project_id": 1,
        "task_id": 9,
        "scope": "standard",
        "template_name": "普通模板",
        "charge_mode": "IAP",
        "series_id": 8,
        "book_name": "项目剧",
        "estimate_publish_date": date(2026, 10, 1),
        "drama_type": "漫剧",
        "channel": "番茄",
        "pitcher_id": 3,
        "pitcher_name": "甲",
        "department_id": 10,
        "department_name": "投放一部",
        "video_ids": (),
    }
    values.update(kwargs)
    return ProjectCard(**values)  # type: ignore[arg-type]


def video(**kwargs: object) -> VideoCard:
    values: dict[str, object] = {
        "video_id": 12,
        "name": "开场",
        "series_id": 8,
        "book_name": "视频剧",
        "estimate_publish_date": DAY,
        "material_type": "vertical_video",
        "ownership": "public",
        "file_url": "https://cdn/a.mp4",
        "uploader_id": 4,
        "uploader_name": "剪辑",
        "uploader_department_id": 10,
        "uploader_department_name": "投放一部",
        "pitcher_ids": (3,),
        "pitcher_names": ("甲",),
    }
    values.update(kwargs)
    return VideoCard(**values)  # type: ignore[arg-type]


def raw(**kwargs: object) -> RawMaterial:
    values: dict[str, object] = {
        "stat_date": DAY,
        "material_id": 12,
        "material_name": "开场",
        "promotion_id": 101,
        "promotion_name": "广告甲",
        "project_id": 1,
        "project_name": "项目甲",
        "stat_cost": Decimal("10"),
        "recovery": Decimal("4"),
        "show_cnt": 2000,
        "click_cnt": 100,
        "convert_cnt": 5,
    }
    values.update(kwargs)
    return RawMaterial(**values)  # type: ignore[arg-type]


class RoiTests(unittest.TestCase):
    def test_ocean_material_id_is_not_a_library_primary_key(self) -> None:
        self.assertEqual(library_ids([12, 7690362566661455899, 0, -1]), [12])

    def test_overlap_uses_newest_created_and_uncovered_day_is_one(self) -> None:
        spans = [span(1, DAY, DAY, "1.20", 8), span(2, DAY, DAY, "1.50", 9)]
        self.assertEqual(roi_for(DAY, spans), Decimal("1.50"))
        self.assertEqual(roi_for(NEXT, spans), Decimal("1.00"))

    def test_profit_sums_each_days_own_roi(self) -> None:
        rows = [
            _profit_slice(DAY, "100", "100"),
            _profit_slice(NEXT, "100", "200"),
        ]
        spans = [span(1, DAY, DAY, "1.00", 1), span(2, NEXT, NEXT, "2.00", 1)]
        table, summary = profit_table(rows, spans, "pitcher")
        self.assertEqual(len(table), 1)
        self.assertEqual(table[0]["profit"], -15.0)
        self.assertEqual(table[0]["recovery_rate"], 1.5)
        self.assertEqual(summary["profit"], -15.0)


class NobidAndRateTests(unittest.TestCase):
    def test_standard_nb_or_cbo_is_nobid_and_uni_is_not(self) -> None:
        self.assertTrue(is_nobid("standard", "玄幻NB模板"))
        self.assertTrue(is_nobid("standard", "cbo放量"))
        self.assertFalse(is_nobid("uni", "玄幻NB模板"))

    def test_cost_ex_nobid_subtracts_only_standard_nobid(self) -> None:
        rows = [
            _material(scope="standard", nobid=True, cost="2444.91", uploader=4),
            _material(scope="standard", nobid=False, cost="2306.15", uploader=4, material=2),
            _material(scope="uni", nobid=False, cost="12.70", recovery="3", uploader=4, material=3),
        ]
        table, summary = editor_spend_table(rows, uploader_id=None, department_id=None, avg_roi=0.2)
        self.assertEqual(table[0]["stat_cost"], 4763.76)
        self.assertEqual(table[0]["standard_nobid_cost"], 2444.91)
        self.assertEqual(table[0]["cost_ex_nobid"], 2318.85)
        self.assertEqual(table[0]["uni_gmv"], 3.0)
        self.assertIsNone(summary["group_avg_roi"])

    def test_cpm_multiplies_by_one_thousand(self) -> None:
        rows = [_material(show=2000, click=100, convert=5, cost="10")]
        table, _summary = material_detail_table(rows, video_id=1, ocean_material_id=None, delivery="all")
        self.assertEqual(table[0]["cpm"], 5.0)
        self.assertEqual(table[0]["ctr"], 5.0)
        self.assertEqual(table[0]["cpc"], 0.1)


class VisibilityTests(unittest.TestCase):
    def test_new_drama_is_estimate_inside_the_query_range(self) -> None:
        self.assertEqual(drama_band(DAY, DAY, NEXT), "新剧")
        self.assertEqual(drama_band(date(2026, 10, 12), DAY, NEXT), "老剧")
        self.assertIsNone(drama_band(date(2026, 10, 15), DAY, NEXT))

    def test_editor_and_pitcher_locks(self) -> None:
        self.assertTrue(editor_only(owner=False, admin=False, role_names=["剪辑师"], tag_names=[]))
        self.assertTrue(editor_only(owner=False, admin=False, role_names=[], tag_names=["素材手"]))
        self.assertFalse(editor_only(owner=True, admin=False, role_names=["剪辑师"], tag_names=["素材手"]))
        self.assertFalse(editor_only(owner=False, admin=True, role_names=["剪辑师"], tag_names=[]))
        self.assertEqual(locked_pitcher(owner=False, admin=False, user_id=3, requested=9), 3)
        self.assertEqual(locked_pitcher(owner=False, admin=True, user_id=3, requested=9), 9)
        self.assertEqual(narrow_departments({10}, 11), set())

    def test_group_roi_uses_the_whole_department_in_the_query(self) -> None:
        rows = [
            _material(uploader=4, department=10, cost="100", recovery="20"),
            _material(uploader=5, department=10, cost="100", recovery="80", material=2),
            _material(uploader=6, department=11, cost="100", recovery="90", material=3),
        ]
        self.assertEqual(group_avg_roi(rows, 10), 0.5)
        table, _summary = editor_spend_table(rows, uploader_id=4, department_id=None, avg_roi=0.5)
        self.assertEqual([row["uploader_id"] for row in table], [4])
        self.assertEqual(table[0]["group_avg_roi"], 0.5)

    def test_iaa_tab_keeps_iaa_of_both_scopes(self) -> None:
        standard = _profit_slice(DAY, "10", "1", scope="standard", charge_mode="IAA")
        uni = _profit_slice(DAY, "10", "1", scope="uni", charge_mode="IAA", pitcher_id=8)
        iap = _profit_slice(DAY, "10", "1", scope="standard", charge_mode="IAP", pitcher_id=9)
        visible = [row for row in (standard, uni, iap) if profit_visible(row, mode="iaa", drama_type=None, platform=None, department_ids=None, pitcher_id=None)]
        self.assertEqual({row.pitcher_id for row in visible}, {3, 8})


class ColumnOrderTests(unittest.TestCase):
    def test_project_card_reads_standard_and_uni_rows(self) -> None:
        from app.modules.report.ledger_store import _card

        standard = (100, 9, "NB模板", "IAP", 8, "剧", None, "番茄剧场", 3, "甲", 10, "投放一部")
        card = _card(standard, "standard", "IAP", {"番茄剧场": ("漫剧", "番茄")}, 9)
        self.assertEqual((card.template_name, card.series_id, card.pitcher_id, card.department_name), ("NB模板", 8, 3, "投放一部"))
        self.assertEqual(card.drama_type, "漫剧")
        uni = (200, 4, "全域模板", 8, "剧", None, "鸥溪剧场", 5, "乙", 11, "投放二部")
        uni_card = _card(uni, "uni", "IAA", {"鸥溪剧场": ("漫剧", "鸥溪")}, 4, uni=True)
        self.assertEqual(uni_card.pitcher_id, 5)
        self.assertEqual(uni_card.channel, "鸥溪")
        self.assertEqual(uni_card.charge_mode, "IAA")


class BuildTests(unittest.TestCase):
    def test_unknown_project_is_dropped_and_video_id_wins(self) -> None:
        materials, profits = build_slices(
            [raw(), raw(project_id=99, material_id=99)],
            {1: project(template_name="NB冲量", video_ids=(12,))},
            {12: video()},
        )
        self.assertEqual(len(materials), 1)
        self.assertTrue(materials[0].is_nobid)
        self.assertEqual(materials[0].book_name, "视频剧")
        self.assertEqual(profits[0].drama_type, "漫剧")
        self.assertEqual(profits[0].platform, "tomato")
        self.assertEqual(profits[0].stat_cost, Decimal("10"))

    def test_nb_list_keeps_zero_and_editor_stat_counts_estimate_day(self) -> None:
        rows, summary = nb_table(
            [SeriesCard(8, "甲剧", DAY), SeriesCard(9, "乙剧", DAY)],
            {8: 2},
            series_name=None,
        )
        self.assertEqual([row["material_count"] for row in rows], [2, 0])
        self.assertEqual(summary["material_count"], 2)
        stats, _ = editor_stat_table(
            [
                _material(estimate=DAY, cost="1"),
                _material(estimate=date(2026, 10, 1), cost="2", material=2, series=9),
            ],
            uploader_id=None,
            department_id=None,
        )
        self.assertEqual(stats[0]["new_drama_count"], 1)
        self.assertEqual(stats[0]["drama_count"], 2)
        self.assertEqual(stats[0]["material_count"], 2)

    def test_drama_editor_summary_counts_a_series_once(self) -> None:
        rows, summary = drama_editor_table(
            [
                _material(uploader=4, series=8),
                _material(uploader=5, series=8, material=2),
            ],
            {8: 6},
            start=DAY,
            end=DAY,
            series_name=None,
            uploader_id=None,
            ages=[],
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(summary["material_count"], 6)


def _profit_slice(
    day: date,
    cost: str,
    recovery: str,
    *,
    scope: str = "standard",
    charge_mode: str = "IAP",
    pitcher_id: int = 3,
) -> object:
    from app.modules.report.ledger import ProfitSlice

    return ProfitSlice(
        stat_date=day,
        scope=scope,
        charge_mode=charge_mode,
        drama_type="漫剧",
        platform="tomato",
        department_id=10,
        department_name="投放一部",
        pitcher_id=pitcher_id,
        pitcher_name="甲",
        stat_cost=Decimal(cost),
        recovery=Decimal(recovery),
    )


def _material(
    *,
    scope: str = "standard",
    nobid: bool = False,
    cost: str = "10",
    recovery: str = "0",
    uploader: int = 4,
    department: int = 10,
    material: int = 1,
    series: int = 8,
    show: int = 0,
    click: int = 0,
    convert: int = 0,
    estimate: date | None = DAY,
) -> MaterialSlice:
    return MaterialSlice(
        stat_date=DAY,
        ocean_material_id=material,
        promotion_id=100 + material,
        promotion_name="广告",
        project_id=1,
        project_name="项目",
        scope=scope,
        is_nobid=nobid,
        charge_mode="IAP" if scope == "standard" else "IAA",
        series_id=series,
        book_name="甲剧",
        estimate_publish_date=estimate,
        video_id=material,
        material_name="素材",
        material_type="vertical_video",
        ownership="public",
        file_url="",
        uploader_id=uploader,
        uploader_name="剪辑",
        uploader_department_id=department,
        uploader_department_name="投放一部",
        pitcher_id=3,
        pitcher_name="甲",
        stat_cost=Decimal(cost),
        recovery=Decimal(recovery),
        show_cnt=show,
        click_cnt=click,
        convert_cnt=convert,
    )


if __name__ == "__main__":
    unittest.main()
