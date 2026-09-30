"""模板、草稿、自动规则的入参、筛选，以及标准号不按投手过滤。"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from app.core.envelope import ApiError
from app.core.times import BEIJING
from app.modules.account.model import AdvertiserAccount, DeliverySubject, DouyinAccount, ProductLibrary
from app.modules.material.model import ManhuaSeries
from app.modules.material_title.model import MaterialTitle
from app.modules.material_video.model import MaterialVideo
from app.modules.standard_delivery.crud import (
    owned_advertisers_stmt,
    standard_douyin_stmt,
    standard_template_by_id_stmt,
    template_name_taken_stmt,
    visible_videos_stmt,
)
from app.modules.standard_delivery.model import DeliveryTaskAccount, DeliveryTaskDraft, DeliveryTemplate
from app.modules.standard_delivery.schema import DraftQuery, DraftWrite, RuleWrite, TemplateQuery, TemplateWrite
from app.modules.standard_delivery.service import (
    create_draft,
    create_template,
    draft_filters,
    panel_tokens,
    require_panels,
    template_filters,
)

CREATED = datetime(2026, 9, 29, 12, 0, 0, tzinfo=BEIJING)
ALLOWED = {"IAA", "IAP"}


class FakeResult:
    """假 execute 结果。"""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalar_one_or_none(self) -> Any:
        """返回首行，没有则 None。"""
        return self._rows[0] if self._rows else None

    def one_or_none(self) -> Any:
        """返回首行元组或实体，没有则 None。"""
        return self._rows[0] if self._rows else None

    def scalars(self) -> FakeResult:
        """让 scalars().all() 走同一份行。"""
        return self

    def all(self) -> list[Any]:
        """返回全部预置行。"""
        return self._rows


class FakeSession:
    """假会话：execute 按顺序吐预置结果。"""

    def __init__(self, results: list[list[Any]]) -> None:
        self.results = list(results)
        self.added: list[Any] = []
        self.commits = 0

    async def execute(self, _statement: Any) -> FakeResult:
        """不看 SQL，按调用次序返回下一份预置结果。用尽后给空结果，方便替换关联行时的删除。"""
        rows = self.results.pop(0) if self.results else []
        return FakeResult(rows)

    def add(self, row: Any) -> None:
        """记下待插入行。"""
        self.added.append(row)

    async def flush(self) -> None:
        """给还没有 id 的父行补一个 id。"""
        for row in self.added:
            if getattr(row, "id", None) is None:
                row.id = 40

    async def commit(self) -> None:
        """记一次提交。"""
        self.commits += 1

    async def refresh(self, row: Any) -> None:
        """补上库里才有的时间。"""
        row.id = row.id or 40
        row.created_date = row.created_date or CREATED
        row.updated_date = CREATED


def make_subject(**kwargs: Any) -> DeliverySubject:
    """造一条标准投放主体。"""
    row = DeliverySubject(
        name=kwargs.get("name", "甲主体"),
        subject_no=100,
        delivery_mode=kwargs.get("delivery_mode", "standard"),
        theater_name="番茄",
        theater_kind="端原生",
        charge_mode=kwargs.get("charge_mode", "IAA"),
        min_bid=Decimal("1.00"),
        max_bid=Decimal("2.00"),
        material_account_id=1,
        dual_bid=False,
        bid_panel=kwargs.get("bid_panel", "面板A,面板B"),
    )
    row.id = kwargs.get("id", 7)
    return row


def template_body(**kwargs: Any) -> TemplateWrite:
    """一份合法的免费模板入参。"""
    data: dict[str, Any] = {
        "name": " 免费模板 ",
        "charge_mode": "IAA",
        "subject_id": 7,
        "bid_panels": [],
        "ads_per_account": 2,
    }
    data.update(kwargs)
    return TemplateWrite(**data)


def draft_body(**kwargs: Any) -> DraftWrite:
    """一份合法的草稿入参。抖音号是单个 id。"""
    data: dict[str, Any] = {
        "template_id": 11,
        "advertiser_ids": [90001, 90002],
        "douyin_account_id": 4,
        "series_id": 8,
        "video_ids": [15],
        "title_ids": [21],
        "placement": "aweme",
        "project_budget": "100.00",
        "ad_budget": "50.50",
        "optimize_goal": "AD_CONVERT_TYPE_ACTIVE",
        "library_no": 77001,
    }
    data.update(kwargs)
    return DraftWrite(**data)


class PanelTests(unittest.TestCase):
    def test_split_keeps_order_and_drops_blanks(self) -> None:
        """逗号、顿号、分号都拆，重复的只留第一次。"""
        self.assertEqual(panel_tokens(" 面板A,面板B、面板A；面板C "), ["面板A", "面板B", "面板C"])

    def test_paid_template_needs_a_panel(self) -> None:
        """付费模板不给出价面板，入参直接拒。"""
        with self.assertRaises(ValidationError):
            template_body(charge_mode="IAP", bid_panels=[])

    def test_panel_must_belong_to_the_subject(self) -> None:
        """选出的面板不在主体上则 400。"""
        with self.assertRaises(ApiError) as caught:
            require_panels("IAP", ["别的"], "面板A,面板B")
        self.assertEqual(caught.exception.status_code, 400)

    def test_free_template_can_skip_panels(self) -> None:
        """免费模板可以不选出价面板。"""
        require_panels("IAA", [], None)


class BodyTests(unittest.TestCase):
    def test_template_name_is_stripped(self) -> None:
        """模板名称去首尾空白。"""
        self.assertEqual(template_body().name, "免费模板")

    def test_one_douyin_rejects_a_list(self) -> None:
        """一次任务只有一个抖音号，传数组直接拒。"""
        with self.assertRaises(ValidationError):
            draft_body(douyin_account_id=[4, 5])

    def test_schedule_must_be_a_pair(self) -> None:
        """预约只填开始、不填结束则拒。"""
        with self.assertRaises(ValidationError):
            draft_body(schedule_start="2026-09-29T10:00:00+08:00")

    def test_duplicate_accounts_are_rejected(self) -> None:
        """账户列表不能重复。"""
        with self.assertRaises(ValidationError):
            draft_body(advertiser_ids=[90001, 90001])

    def test_rule_ranges_must_be_pairs(self) -> None:
        """消耗只填下限则拒。短剧可以多选。"""
        with self.assertRaises(ValidationError):
            RuleWrite(name="规则甲", template_id=11, series_ids=[8, 9], cost_min="1")


class FilterTests(unittest.TestCase):
    def _sql(self, items: list[Any]) -> str:
        """把过滤条件编译成字面量 SQL。"""
        return " AND ".join(str(item.compile(compile_kwargs={"literal_binds": True})) for item in items)

    def test_template_filters_charge_and_subject(self) -> None:
        """模板按收费模式和主体精确筛选，并排除软删。"""
        sql = self._sql(template_filters(TemplateQuery(charge_mode="IAP", subject_id=7)))
        self.assertIn("delivery_template.is_deleted = 0", sql)
        self.assertIn("delivery_template.delivery_mode = 'standard'", sql)
        self.assertIn("delivery_template.charge_mode = 'IAP'", sql)
        self.assertIn("delivery_template.subject_id = 7", sql)

    def test_standard_lookup_ignores_uni_templates(self) -> None:
        """按 id 取模板和重名检查都只看标准行，全域同名不挡。"""
        by_id = str(standard_template_by_id_stmt(11).compile(compile_kwargs={"literal_binds": True}))
        taken = str(template_name_taken_stmt("IAA", "免费模板", None).compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("delivery_template.delivery_mode = 'standard'", by_id)
        self.assertIn("delivery_template.delivery_mode = 'standard'", taken)
        self.assertNotIn("delivery_mode = 'uni'", by_id)

    def test_draft_filters_are_scoped_to_the_pitcher(self) -> None:
        """草稿只看当前投手，并能按短剧、预约筛选。"""
        sql = self._sql(draft_filters(DraftQuery(charge_mode="IAA", series_id=8, scheduled=True), 3))
        self.assertIn("delivery_task_draft.pitcher_user_id = 3", sql)
        self.assertIn("delivery_task_draft.series_id = 8", sql)
        self.assertIn("delivery_task_draft.schedule_start IS NOT NULL", sql)

    def test_standard_douyin_is_shared(self) -> None:
        """标准号只看启用，不读投手分配表。"""
        sql = str(standard_douyin_stmt(4).compile(compile_kwargs={"literal_binds": True}))
        where = sql.split("WHERE", 1)[1]
        self.assertIn("douyin_account.delivery_mode = 'standard'", where)
        self.assertIn("douyin_account.enabled IS true", where)
        self.assertNotIn("douyin_pitcher", sql)
        self.assertNotIn("owner_user_id", where)

    def test_advertisers_belong_to_the_current_pitcher(self) -> None:
        """账户下拉只取当前投手名下仍然有效的户。"""
        sql = str(owned_advertisers_stmt([90001], 3).compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("advertiser_account.pitcher_user_id = 3", sql)
        self.assertIn("advertiser_account.sync_status = 'active'", sql)

    def test_videos_stay_on_the_series(self) -> None:
        """视频须落在所选短剧上。"""
        sql = str(visible_videos_stmt([15], 8, 3).compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("material_videos.series_id = 8", sql)
        self.assertIn("material_videos.id IN (15)", sql)


class CreateTemplateTests(unittest.TestCase):
    def test_missing_subject_is_not_found(self) -> None:
        """主体不存在 404，不写。"""
        session = FakeSession([[]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_template(session, template_body(), ALLOWED))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(session.added, [])

    def test_uni_subject_is_rejected(self) -> None:
        """全域主体不能挂到标准投放模板上。"""
        session = FakeSession([[make_subject(delivery_mode="uni")]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_template(session, template_body(), ALLOWED))
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(session.commits, 0)

    def test_new_template_keeps_panels_and_ads(self) -> None:
        """新增后带出主体名称，名称已去空白。"""
        session = FakeSession([[make_subject()], []])
        item = asyncio.run(create_template(session, template_body(bid_panels=["面板A"]), ALLOWED))
        self.assertEqual(item["name"], "免费模板")
        self.assertEqual(item["subject_name"], "甲主体")
        self.assertEqual(item["bid_panels"], ["面板A"])
        self.assertEqual(item["ads_per_account"], 2)
        self.assertEqual(session.commits, 1)
        row = session.added[0]
        self.assertEqual(row.delivery_mode, "standard")
        self.assertIsNone(row.project_budget)
        self.assertIsNone(row.roi_coefficient)
        self.assertIsNone(row.aigc_dynamic_creative)
        self.assertIsNone(row.title_select_mode)


class CreateDraftTests(unittest.TestCase):
    def _ready(self) -> tuple[DeliveryTemplate, DeliverySubject, DouyinAccount, ManhuaSeries, list[AdvertiserAccount], MaterialVideo, MaterialTitle, ProductLibrary]:
        """拼一份能通过校验的现成数据。"""
        subject = make_subject()
        template = DeliveryTemplate(
            name="免费模板",
            charge_mode="IAA",
            subject_id=7,
            bid_panels=[],
            ads_per_account=2,
        )
        template.id = 11
        template.created_date = CREATED
        template.updated_date = CREATED
        douyin = DouyinAccount(aweme_id="aweme-1", name="标准号", delivery_mode="standard", enabled=True)
        douyin.id = 4
        series = ManhuaSeries(book_name="甲剧")
        series.id = 8
        accounts = []
        for ocean_id, name in ((90001, "户A"), (90002, "户B")):
            account = AdvertiserAccount(
                organization_id=1,
                oe_app_id=1,
                advertiser_id=ocean_id,
                name=name,
                sync_status="active",
                pitcher_user_id=3,
            )
            account.id = ocean_id
            accounts.append(account)
        video = MaterialVideo(
            name="甲视频",
            material_type="vertical_video",
            file_urls=["https://example.com/a.mp4"],
            series_id=8,
            platform="tomato",
            tag_id=1,
            ownership="public",
            uploader_id=3,
        )
        video.id = 15
        title = MaterialTitle(title="标题一", category="common", uploader_id=3)
        title.id = 21
        library = ProductLibrary(
            name="视频库",
            library_no=77001,
            library_kind="video",
            organization_id=1,
            library_role="fallback",
        )
        library.id = 6
        return template, subject, douyin, series, accounts, video, title, library

    def test_two_accounts_share_one_aweme(self) -> None:
        """两个账户写在同一条草稿上，抖音号只有一个。"""
        template, subject, douyin, series, accounts, video, title, library = self._ready()
        session = FakeSession([[(template, subject)], [douyin], [series], accounts, [video], [title], [library]])
        item = asyncio.run(create_draft(session, draft_body(), 3, ALLOWED))
        self.assertEqual(item["aweme_id"], "aweme-1")
        self.assertEqual(item["douyin_account_id"], "4")
        self.assertEqual([row["advertiser_id"] for row in item["accounts"]], [90001, 90002])
        drafts = [row for row in session.added if isinstance(row, DeliveryTaskDraft)]
        links = [row for row in session.added if isinstance(row, DeliveryTaskAccount)]
        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0].douyin_account_id, 4)
        self.assertEqual(len(links), 2)
        self.assertEqual(session.commits, 1)

    def test_disabled_or_uni_douyin_is_rejected(self) -> None:
        """不是已启用标准号时 400，并且不写草稿。"""
        template, subject, *_rest = self._ready()
        session = FakeSession([[(template, subject)], []])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_draft(session, draft_body(), 3, ALLOWED))
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(caught.exception.message, "抖音号不是已启用的标准号")
        self.assertFalse(any(isinstance(row, DeliveryTaskDraft) for row in session.added))


if __name__ == "__main__":
    unittest.main()
