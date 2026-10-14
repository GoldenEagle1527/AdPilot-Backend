"""账户列表：日期成对，除数为 0 时比率是空。"""

from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.dialects.mysql import dialect as mysql_dialect
from sqlalchemy.dialects.postgresql import dialect as postgresql_dialect

from app.modules.account.model import AdvertiserAccount
from app.modules.ocean_ads.columns import kept_fixed
from app.modules.ocean_ads.schema import (
    AccountQuery,
    ColumnQuery,
    ColumnWrite,
    MaterialQuery,
    ProjectBudgetWrite,
    PromotionQuery,
)
from app.modules.ocean_ads.service import _matches_kind, _money, _rate, effect_numbers, metrics_statement
from app.modules.ocean_ads.pages import (
    accepted_delete_ids,
    accepted_status_ids,
    batch_status,
    list_materials,
    project_status_label,
    promotion_status_label,
    apply_reject_reasons,
    project_create_outcome,
    reject_lines,
    _aweme_from_template,
    _labels,
    _seven,
    roi_text,
    stored_budget_mode,
)
from app.modules.oceanengine.delivery import _payload_budget, _payload_links, creative_material_id


class RateTest(unittest.TestCase):
    """产品确认：两位小数，四舍五入。分母是 0 直接展示 0。"""

    def test_zero_divisor_is_zero(self) -> None:
        self.assertEqual(_rate(Decimal("1"), Decimal(0)), "0.00")

    def test_divides_and_rounds_half_up(self) -> None:
        self.assertEqual(_rate(Decimal("1"), Decimal("4")), "0.25")
        self.assertEqual(_rate(Decimal("1"), Decimal("6")), "0.17")


class StatusLabelTest(unittest.TestCase):
    """项目状态只传开启和暂停。父项目暂停时广告跟着显示已被项目暂停。"""

    def test_project_labels(self) -> None:
        self.assertEqual(project_status_label("ENABLE"), "开启")
        self.assertEqual(project_status_label("DISABLE"), "暂停")

    def test_parent_pause_wins(self) -> None:
        self.assertEqual(promotion_status_label("ENABLE", "DISABLE"), "已被项目暂停")
        self.assertEqual(promotion_status_label("DISABLE", "ENABLE"), "已暂停")
        self.assertEqual(promotion_status_label("ENABLE", "ENABLE"), "投放中")


class AccountQueryTest(unittest.TestCase):
    """日期必须成对。页签可以不传，不传则标准和全域都展示。"""

    def test_tab_is_optional(self) -> None:
        query = AccountQuery()
        self.assertIsNone(query.delivery_kind)

    def test_rejects_half_range(self) -> None:
        with self.assertRaises(ValidationError):
            AccountQuery(delivery_kind="standard", date_start=date(2026, 10, 1))

    def test_account_id_is_optional(self) -> None:
        query = AccountQuery(delivery_kind="uni", account_id=1873916032590219)
        self.assertEqual(query.account_id, 1873916032590219)


class BatchStatusTest(unittest.TestCase):
    """批量三个按钮：开启、暂停改开关，删除走软删除。"""

    def test_actions(self) -> None:
        self.assertEqual(batch_status("开启"), "ENABLE")
        self.assertEqual(batch_status("暂停"), "DISABLE")
        self.assertIsNone(batch_status("删除"))


class PromotionLinkTest(unittest.TestCase):
    """推广外链按完整链接精确匹配。创建广告时从报文抄下整段链接。"""

    def test_query_keeps_full_url(self) -> None:
        link = "https://example.com/promo/1"
        query = PromotionQuery(promotion_link=link)
        self.assertEqual(query.promotion_link, link)

    def test_reads_links_from_create_payload(self) -> None:
        payload = {
            "project_id": 7000000000000001,
            "promotion_materials": {"playlet_series_url_list": [" https://example.com/promo/1 ", ""]},
        }
        self.assertEqual(_payload_links(payload), ["https://example.com/promo/1"])


class AcceptedStatusIdsTest(unittest.TestCase):
    """巨量回包里的 id 列表是成功的，errors 里的不算。"""

    def test_empty_data_means_the_batch_succeeded(self) -> None:
        ok, messages = accepted_status_ids({"data": {}}, "project_ids", [11, 12])
        self.assertEqual(ok, [11, 12])
        self.assertEqual(messages, [])

    def test_error_id_is_left_out(self) -> None:
        remote = {
            "data": {
                "project_ids": [11],
                "errors": [{"project_id": 12, "error_message": "已删除"}],
            }
        }
        ok, messages = accepted_status_ids(remote, "project_ids", [11, 12])
        self.assertEqual(ok, [11])
        self.assertEqual(messages, ["已删除"])

    def test_delete_without_success_ids_is_not_deleted(self) -> None:
        ok, messages = accepted_delete_ids({"data": {}}, "promotion_ids", [11, 12])
        self.assertEqual(ok, [])
        self.assertEqual(messages, ["11 未返回删除成功", "12 未返回删除成功"])
        ok, messages = accepted_delete_ids({"data": {"promotion_ids": [11]}}, "promotion_ids", [11, 12])
        self.assertEqual(ok, [11])
        self.assertEqual(messages, ["12 未返回删除成功"])


class EffectNumberTest(unittest.TestCase):
    """千次费用不乘 1000。转化率是百分数。分母是 0 时是 0.00。"""

    def test_divides_each_formula(self) -> None:
        fields = effect_numbers(Decimal("10"), Decimal("4"), Decimal("8"), 100, 20, 4, 2)
        self.assertEqual(fields["revenue_today"], "4.00")
        self.assertEqual(fields["revenue_total"], "8.00")
        self.assertEqual(fields["recycle_amount"], "8.00")
        self.assertEqual(fields["revenue_today_rate"], "0.40")
        self.assertEqual(fields["revenue_total_rate"], "0.80")
        self.assertEqual(fields["cpm"], "0.10")
        self.assertEqual(fields["ctr"], "0.20")
        self.assertEqual(fields["cpc"], "0.50")
        self.assertEqual(fields["convert_cost"], "2.50")
        self.assertEqual(fields["convert_rate"], "20.00")
        self.assertEqual(fields["active_cost"], "5.00")
        self.assertEqual(fields["active_arpu"], "4.00")

    def test_zero_divisors_are_zero(self) -> None:
        fields = effect_numbers(Decimal(0), Decimal("1"), Decimal("1"), 0, 0, 0, 0)
        self.assertEqual(fields["revenue_today_rate"], "0.00")
        self.assertEqual(fields["cpm"], "0.00")
        self.assertEqual(fields["ctr"], "0.00")
        self.assertEqual(fields["cpc"], "0.00")
        self.assertEqual(fields["convert_cost"], "0.00")
        self.assertEqual(fields["convert_rate"], "0.00")
        self.assertEqual(fields["active_cost"], "0.00")
        self.assertEqual(fields["active_arpu"], "0.00")


class RoiAndRejectTest(unittest.TestCase):
    """全域 ROI 读项目列表的 roi_goal。审核原因来自广告和素材两段。"""

    def test_roi_keeps_four_decimals(self) -> None:
        self.assertEqual(roi_text({"delivery_setting": {"roi_goal": "1.019"}}), "1.019")
        self.assertIsNone(roi_text({"delivery_setting": {}}))
        self.assertIsNone(roi_text({}))

    def test_reject_lines_keep_order_and_drop_blanks(self) -> None:
        item = {
            "promotion_reject": [{"reject_reason": ["标题违规", " "]}],
            "material_reject": [{"reject_reason": ["标题违规", "低质"]}],
        }
        self.assertEqual(reject_lines(item), ["标题违规", "低质"])

    def test_create_failure_keeps_ocean_message(self) -> None:
        self.assertEqual(project_create_outcome("名称重复"), ("创建失败", "名称重复"))
        self.assertEqual(project_create_outcome(None), ("创建成功", None))

    def test_reject_lookup_failure_is_dash(self) -> None:
        rows = [{"promotion_id": 1}, {"promotion_id": 2}]
        apply_reject_reasons(rows, {1: []}, {2})
        self.assertEqual(rows[0]["reject_reasons"], [])
        self.assertEqual(rows[1]["reject_reasons"], ["-"])

    def test_upload_material_id_is_the_creative_id(self) -> None:
        self.assertEqual(creative_material_id({"data": {"material_id": 7689529919781474991}}), 7689529919781474991)
        self.assertIsNone(creative_material_id({"data": {"video_id": "local-1"}}))
        self.assertIsNone(creative_material_id({}))


class ColumnAndBudgetTest(unittest.TestCase):
    """自定义列必须属于该页。广告预算从创建报文抄下来。"""

    def test_get_columns_accepts_menu_id_as_text(self) -> None:
        self.assertEqual(ColumnQuery(menu_id="32").menu_id, 32)
        self.assertEqual(ColumnQuery(menu_id="35").menu_id, 35)
        with self.assertRaises(ValidationError):
            ColumnQuery(menu_id="36")

    def test_fixed_columns_must_be_selected_and_at_most_five(self) -> None:
        saved = ColumnWrite(menu_id=32, columns=["account_name", "balance"], fixed_columns=["account_name"])
        self.assertEqual(saved.fixed_columns, ["account_name"])
        self.assertEqual(kept_fixed(None, ["account_name"]), [])
        self.assertEqual(kept_fixed(["balance", "balance", "missing"], ["balance"]), ["balance"])
        with self.assertRaises(ValidationError):
            ColumnWrite(menu_id=32, columns=["account_name"], fixed_columns=["balance"])
        with self.assertRaises(ValidationError):
            ColumnWrite(
                menu_id=32,
                columns=["account_name", "account_id", "balance", "stat_cost", "show_cnt", "click_cnt"],
                fixed_columns=["account_name", "account_id", "balance", "stat_cost", "show_cnt", "click_cnt"],
            )

    def test_unknown_or_duplicate_column_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ColumnWrite(menu_id=32, columns=["stat_cost", "not_a_column"])
        with self.assertRaises(ValidationError):
            ColumnWrite(menu_id=33, columns=["project_id", "project_id"])

    def test_budget_is_positive_money(self) -> None:
        body = ProjectBudgetWrite(project_ids=[1], budget=Decimal("300.50"))
        self.assertEqual(body.budget, Decimal("300.50"))
        with self.assertRaises(ValidationError):
            ProjectBudgetWrite(project_ids=[1], budget=Decimal("0"))

    def test_uni_face_labels_keep_order(self) -> None:
        self.assertEqual(_labels(["甲剧", "甲剧", None, "乙剧"]), "甲剧、乙剧")
        self.assertIsNone(_labels([None, " "]))
        self.assertEqual(_aweme_from_template({"native_setting": {"aweme_id": "aweme-a"}}), "aweme-a")

    def test_budget_update_keeps_the_mode_saved_at_create(self) -> None:
        self.assertEqual(stored_budget_mode({"delivery_setting": {"budget_mode": "BUDGET_MODE_DAY"}}), "BUDGET_MODE_DAY")
        self.assertEqual(stored_budget_mode(None), "BUDGET_MODE_DAY")

    def test_payload_budget(self) -> None:
        self.assertEqual(_payload_budget({"budget": "12.5"}), Decimal("12.50"))
        self.assertIsNone(_payload_budget({"budget": 0}))
        self.assertIsNone(_payload_budget({}))


def _pg_sql(statement: object) -> str:
    return " ".join(str(statement.compile(dialect=postgresql_dialect())).split())  # type: ignore[attr-defined]


class AccountKindByPromotionTest(unittest.TestCase):
    """3.5.1：素材行按广告 id 到 oe_promotion，再取广告所属项目挂的主体。"""

    def test_metrics_join_through_the_promotion(self) -> None:
        query = AccountQuery(delivery_kind="uni", charge_mode="IAP")
        sql = _pg_sql(metrics_statement([1877368580368602], query))
        self.assertIn("oe_promotion.advertiser_id = oe_material_report.advertiser_id", sql)
        self.assertIn("oe_promotion.promotion_id = oe_material_report.cdp_promotion_id", sql)
        self.assertIn("oe_project.ocean_project_id = oe_promotion.ocean_project_id", sql)
        self.assertNotIn("oe_material_report.cdp_project_id", sql)
        self.assertIn("oe_promotion.is_deleted", sql)
        self.assertIn("delivery_subject.delivery_mode", sql)
        self.assertIn("delivery_subject.charge_mode", sql)

    def test_tab_needs_an_ad_of_that_kind(self) -> None:
        query = AccountQuery(delivery_kind="standard")
        sql = _pg_sql(select(AdvertiserAccount.id).where(_matches_kind(query)))
        self.assertIn("EXISTS (SELECT oe_promotion.id FROM oe_promotion", sql)
        self.assertIn("oe_promotion.advertiser_id = advertiser_account.advertiser_id", sql)
        self.assertIn("oe_project.ocean_project_id = oe_promotion.ocean_project_id", sql)


class MaterialDeletedFilterTest(unittest.IsolatedAsyncioTestCase):
    """所属项目或广告已软删的素材不出现。广告 NOT EXISTS 必须保留自己的 FROM。"""

    async def test_both_not_exists_compile(self) -> None:
        class Session:
            def __init__(self) -> None:
                self.statements: list = []

            async def execute(self, statement):
                self.statements.append(statement)

                class Result:
                    def all(self) -> list:
                        return []

                return Result()

        session = Session()
        data = await list_materials(
            session,
            MaterialQuery(stat_date=date(2026, 10, 14), page=1, page_size=5),
            {"id": 1, "data_scope": {"self_only": True, "department_ids": []}},
        )
        self.assertEqual(data["list"], [])
        self.assertEqual(data["total"], 0)
        sql = " ".join(str(session.statements[0].compile(dialect=mysql_dialect())).split())
        self.assertIn("NOT (EXISTS (SELECT oe_promotion.id FROM oe_promotion", sql)
        self.assertIn("oe_promotion.is_deleted", sql)
        self.assertIn("NOT (EXISTS (SELECT oe_project.id FROM oe_project", sql)
        self.assertIn("oe_project.is_deleted", sql)


class UniEmptyCostTest(unittest.TestCase):
    """没有报表行时全域项目消耗是两位小数 0。"""

    def test_missing_metric_is_zero_money(self) -> None:
        self.assertEqual(_money(_seven(None)[0]), "0.00")
        source = (
            Path(__file__).resolve().parents[3] / "app" / "modules" / "ocean_ads" / "pages.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"stat_cost": _money(_seven(metric)[0]),', source)
        self.assertNotIn("if metric else 0", source)


if __name__ == "__main__":
    unittest.main()
