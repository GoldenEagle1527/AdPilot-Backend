"""端原生投放任务的本地保存、列表和软删。"""

from __future__ import annotations

import asyncio
import unittest
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.core.auth import require_token
from app.core.db import get_session
from app.core.envelope import ApiError, register_exception_handlers
from app.core.times import BEIJING
from app.modules.account.model import AdvertiserAccount, DeliverySubject, DouyinAccount
from app.modules.material_title.model import MaterialTitle
from app.modules.material_video.model import MaterialVideo
from app.modules.standard_delivery.model import DeliveryTemplate
from app.modules.uni_native_task.controller import router
from app.modules.uni_native_task.crud import own_titles_stmt, pitcher_videos_stmt, series_stmt
from app.modules.uni_native_task.model import (
    UniNativeTask,
    UniNativeTaskAccount,
    UniNativeTaskBatchTitle,
    UniNativeTaskLink,
    UniNativeTaskVideo,
)
from app.modules.uni_native_task.schema import TaskQuery, TaskWrite
from app.modules.uni_native_task.service import (
    create_task,
    delete_task,
    get_task,
    list_tasks,
    series_short_name,
    task_filters,
    update_task,
)

CREATED = datetime(2026, 9, 30, 11, 0, tzinfo=BEIJING)
PREFIX = "/api/v1/uni-native-tasks"
MIGRATION = Path(__file__).resolve().parents[3] / "alembic" / "versions" / "20260930_03_uni_native_task.py"


class FakeResult:
    """假 execute 结果。"""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalar_one(self) -> Any:
        """返回唯一一行。分页总数用。"""
        return self._rows[0]

    def one(self) -> Any:
        """返回唯一一行元组。查表是否存在时用。"""
        return self._rows[0]

    def one_or_none(self) -> Any:
        """返回首行，没有则 None。"""
        return self._rows[0] if self._rows else None

    def scalars(self) -> FakeResult:
        """让 scalars().all() 走同一份行。"""
        return self

    def all(self) -> list[Any]:
        """返回全部预置行。"""
        return self._rows


class FakeSession:
    """假会话：execute 按顺序吐预置结果。用尽后给空结果，方便替换关联行时的删除。"""

    def __init__(self, results: list[list[Any]] | None = None) -> None:
        self.results = list(results or [])
        self.statements: list[Any] = []
        self.added: list[Any] = []
        self.commits = 0

    async def execute(self, statement: Any) -> FakeResult:
        """不看 SQL，按调用次序返回下一份预置结果。"""
        self.statements.append(statement)
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


def make_subject() -> DeliverySubject:
    """造一条全域投放主体。"""
    row = DeliverySubject(
        name="全域主体",
        subject_no=200,
        delivery_mode="uni",
        theater_name="番茄",
        theater_kind="端原生",
        charge_mode="IAA",
        min_bid=Decimal("1.00"),
        max_bid=Decimal("2.00"),
        material_account_id=1,
        dual_bid=False,
    )
    row.id = 7
    return row


def make_template() -> DeliveryTemplate:
    """造一条全域模板。预算和 ROI 用来验证抄写。"""
    row = DeliveryTemplate(
        name="全域甲",
        delivery_mode="uni",
        charge_mode="IAA",
        subject_id=7,
        bid_panels=[],
        ads_per_account=None,
        project_budget=Decimal("100.00"),
        roi_coefficient=Decimal("1.200"),
        aigc_dynamic_creative=True,
        title_select_mode="manual",
    )
    row.id = 11
    row.is_deleted = 0
    row.created_date = CREATED
    row.updated_date = CREATED
    return row


def make_douyin(**kwargs: Any) -> DouyinAccount:
    """造一条抖音号。默认是全域，并且已分给当前投手。"""
    row = DouyinAccount(
        aweme_id=kwargs.get("aweme_id", "aweme-u"),
        name=kwargs.get("name", "全域号"),
        delivery_mode=kwargs.get("delivery_mode", "uni"),
        enabled=True,
    )
    row.id = kwargs.get("id", 4)
    row.is_deleted = 0
    return row


def make_advertiser(**kwargs: Any) -> AdvertiserAccount:
    """造一条当前投手名下的有效广告主。"""
    row = AdvertiserAccount(
        organization_id=1,
        oe_app_id=1,
        advertiser_id=kwargs.get("advertiser_id", 90001),
        name=kwargs.get("name", "账户甲"),
        sync_status="active",
        pitcher_user_id=3,
    )
    row.id = kwargs.get("id", 31)
    row.is_deleted = 0
    return row


def make_video() -> MaterialVideo:
    """造一条属于短剧 8、上传者是当前投手的视频。"""
    row = MaterialVideo(
        name="甲视频",
        material_type="vertical_video",
        file_urls=["https://example.com/a.mp4"],
        series_id=8,
        platform="tomato",
        tag_id=1,
        ownership="private",
        uploader_id=3,
    )
    row.id = 15
    row.is_deleted = 0
    return row


def make_title() -> MaterialTitle:
    """造一条当前投手自己的标题。"""
    row = MaterialTitle(title="标题一", category="common", uploader_id=3)
    row.id = 21
    row.is_deleted = 0
    return row


def make_task(**kwargs: Any) -> UniNativeTask:
    """造一条已保存的任务。"""
    row = UniNativeTask(
        template_id=kwargs.get("template_id", 11),
        pitcher_user_id=kwargs.get("pitcher_user_id", 3),
        series_id=kwargs.get("series_id", 8),
        project_budget=kwargs.get("project_budget", Decimal("66.00")),
        roi_coefficient=kwargs.get("roi_coefficient", Decimal("1.200")),
        status="saved",
        executed_at=None,
    )
    row.id = kwargs.get("id", 40)
    row.is_deleted = 0
    row.created_date = CREATED
    row.updated_date = CREATED
    return row


def tables(*names: str | None) -> list[tuple[str | None, str | None, str | None]]:
    """to_regclass 的一行。缺的表用 None。"""
    series, videos, titles = (list(names) + [None, None, None])[:3]
    return [(series, videos, titles)]


def payload(**kwargs: Any) -> dict[str, Any]:
    """一份合法请求。ROI 默认不传，用来验证从模板抄写。"""
    data: dict[str, Any] = {
        "template_id": 11,
        "series_id": 8,
        "project_budget": "66.5",
        "accounts": [
            {"douyin_account_id": 4, "advertiser_id": 90001},
            {"douyin_account_id": 6, "advertiser_id": 90002},
        ],
        "promotion_links": [
            {"charge_mode": "IAA", "link_text": " https://iaa.example/a "},
            {"charge_mode": "IAP", "link_text": "https://iap.example/b"},
        ],
        "video_ids": [15],
        "title_ids": [21],
        "batch_titles": [" 临时标题 "],
    }
    data.update(kwargs)
    return data


def write_body(**kwargs: Any) -> TaskWrite:
    """校验过的入参。"""
    return TaskWrite(**payload(**kwargs))


def http_client(session: FakeSession, *, login: bool = True) -> TestClient:
    """挂上本模块路由。"""
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)

    async def _session():
        yield session

    app.dependency_overrides[get_session] = _session
    if login:
        app.dependency_overrides[require_token] = lambda: {
            "id": "3",
            "nickname": "投手",
            "login_account": "pitcher",
            "tenant": "agent",
        }
    return TestClient(app)


def _sql(items: list[Any]) -> str:
    """按 PostgreSQL 把过滤条件编成可读 SQL。"""
    dialect = postgresql.dialect()
    return " AND ".join(
        str(item.compile(dialect=dialect, compile_kwargs={"literal_binds": True})) for item in items
    )


class BodyTests(unittest.TestCase):
    def test_short_name_is_the_first_two_characters(self) -> None:
        """简称取剧名前两个字。一个字的剧名就用这一个字。"""
        self.assertEqual(series_short_name("甲壳虫"), "甲壳")
        self.assertEqual(series_short_name("甲"), "甲")

    def test_accounts_are_required_and_unique(self) -> None:
        """至少一对抖音号和账户，而且两边都不能重复。"""
        with self.assertRaises(ValidationError):
            write_body(accounts=[])
        with self.assertRaises(ValidationError):
            write_body(
                accounts=[
                    {"douyin_account_id": 4, "advertiser_id": 90001},
                    {"douyin_account_id": 4, "advertiser_id": 90002},
                ]
            )

    def test_date_range_cannot_run_backwards(self) -> None:
        """日期段起不能晚于止。"""
        with self.assertRaises(ValidationError):
            TaskQuery(date_start=date(2026, 9, 30), date_end=date(2026, 9, 1))

    def test_budget_override_is_optional(self) -> None:
        """不传预算和 ROI 时留空，交给服务去抄模板。"""
        body = TaskWrite(**payload(project_budget=None, roi_coefficient=None))
        self.assertIsNone(body.project_budget)
        self.assertIsNone(body.roi_coefficient)
        self.assertEqual(body.promotion_links[0].link_text, "https://iaa.example/a")
        self.assertEqual(body.batch_titles, ["临时标题"])


class FilterTests(unittest.TestCase):
    def test_list_is_own_tasks_in_a_closed_date_range(self) -> None:
        """只看当前投手。创建日左闭右闭，止日落到次日 0 点之前。剧名模糊。"""
        sql = _sql(
            task_filters(
                TaskQuery(date_start=date(2026, 9, 1), date_end=date(2026, 9, 30), series_name="甲%"),
                3,
            )
        )
        self.assertIn("uni_native_task.is_deleted = 0", sql)
        self.assertIn("uni_native_task.pitcher_user_id = 3", sql)
        self.assertIn("2026-09-01", sql)
        self.assertIn("2026-10-01", sql)
        self.assertIn("manhua_series.book_name", sql)
        self.assertIn("ILIKE", sql)

    def test_series_video_and_title_queries_use_real_tables(self) -> None:
        """短剧只取主键和剧名。视频、标题打真实表，不另造一份。"""
        series = str(series_stmt(8).compile(compile_kwargs={"literal_binds": True}))
        videos = str(pitcher_videos_stmt([15], 8, 3).compile(compile_kwargs={"literal_binds": True}))
        titles = str(own_titles_stmt([21], 3).compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("manhua_series.book_name", series)
        self.assertNotIn("thumb_url", series)
        self.assertIn("material_videos", videos)
        self.assertIn("material_videos.series_id = 8", videos)
        self.assertIn("material_video_pitchers", videos)
        self.assertIn("material_titles", titles)
        self.assertIn("material_titles.uploader_id = 3", titles)

    def test_migration_revises_uni_template_and_skips_missing_catalogs(self) -> None:
        """迁移接在全域模板之后。不建素材表、标题库和剧场表。状态只有 saved。"""
        text = MIGRATION.read_text(encoding="utf-8")
        self.assertIn('down_revision: Union[str, None] = "20260930_02"', text)
        self.assertIn("status = 'saved'", text)
        self.assertIn('["series_id"], ["manhua_series.id"]', text)
        self.assertNotIn('op.create_table(\n        "material_videos"', text)
        self.assertNotIn('op.create_table(\n        "material_titles"', text)
        self.assertNotIn('op.create_table(\n        "manhua_series"', text)
        self.assertNotIn("theater", text)
        self.assertNotIn("执行中", text)


class SaveTests(unittest.TestCase):
    def _ready(self) -> tuple[Any, ...]:
        """模板、两对账户、一条视频、一条标题库标题。"""
        template = make_template()
        subject = make_subject()
        first = make_douyin()
        second = make_douyin(id=6, aweme_id="aweme-v", name="全域乙")
        accounts = [make_advertiser(), make_advertiser(id=32, advertiser_id=90002, name="账户乙")]
        return template, subject, [first, second], accounts, make_video(), make_title()

    def test_create_copies_roi_and_keeps_batch_titles_off_the_library(self) -> None:
        """预算用客户端的，ROI 抄模板。临时标题只留在任务上。状态是 saved。"""
        template, subject, douyins, accounts, video, title = self._ready()
        session = FakeSession(
            [
                [(template, subject)],
                tables("manhua_series", "material_videos", "material_titles"),
                [(8, "甲壳虫")],
                douyins,
                [4, 6],
                accounts,
                [video],
                [title],
            ]
        )
        item = asyncio.run(create_task(session, write_body(), 3))
        self.assertEqual(item["status"], "saved")
        self.assertIsNone(item["executed_at"])
        self.assertEqual(item["template_id"], "11")
        self.assertEqual(item["project_budget"], "66.50")
        self.assertEqual(item["roi_coefficient"], "1.200")
        self.assertEqual(item["book_name"], "甲壳虫")
        self.assertEqual(item["series_short_name"], "甲壳")
        self.assertEqual(
            [(row["douyin_account_id"], row["advertiser_id"]) for row in item["accounts"]],
            [("4", 90001), ("6", 90002)],
        )
        self.assertEqual(item["promotion_links"][0]["link_text"], "https://iaa.example/a")
        self.assertEqual(item["promotion_links"][1]["charge_mode"], "IAP")
        self.assertEqual(item["videos"], [{"id": "15", "name": "甲视频"}])
        self.assertEqual(item["titles"], [{"id": "21", "title": "标题一"}])
        self.assertEqual(item["batch_titles"], ["临时标题"])
        self.assertEqual(item["created_at"], "2026-09-30T11:00:00+08:00")
        stored = next(row for row in session.added if isinstance(row, UniNativeTask))
        self.assertEqual(stored.template_id, 11)
        self.assertEqual(stored.project_budget, Decimal("66.50"))
        self.assertEqual(stored.roi_coefficient, Decimal("1.200"))
        self.assertEqual(stored.status, "saved")
        self.assertIsNone(stored.executed_at)
        self.assertEqual(len([row for row in session.added if isinstance(row, UniNativeTaskAccount)]), 2)
        self.assertEqual(len([row for row in session.added if isinstance(row, UniNativeTaskLink)]), 2)
        self.assertTrue(any(isinstance(row, UniNativeTaskVideo) and row.material_video_id == 15 for row in session.added))
        self.assertTrue(any(isinstance(row, UniNativeTaskBatchTitle) and row.title == "临时标题" for row in session.added))
        self.assertFalse(any(isinstance(row, MaterialTitle) for row in session.added))
        self.assertEqual(session.commits, 1)

    def test_omitted_budget_is_copied_from_the_template(self) -> None:
        """两个金额都不传时，任务上就是模板的数。"""
        template, subject, douyins, accounts, _video, _title = self._ready()
        session = FakeSession(
            [
                [(template, subject)],
                tables("manhua_series", None, None),
                [(8, "甲壳虫")],
                douyins,
                [4, 6],
                accounts,
            ]
        )
        item = asyncio.run(
            create_task(session, write_body(project_budget=None, roi_coefficient=None, video_ids=[], title_ids=[]), 3)
        )
        self.assertEqual(item["project_budget"], "100.00")
        self.assertEqual(item["roi_coefficient"], "1.200")

    def test_missing_video_table_rejects_ids_without_insert(self) -> None:
        """视频表不在库里时，不接受视频 id，也不写任务。"""
        template, subject, douyins, accounts, *_rest = self._ready()
        session = FakeSession(
            [
                [(template, subject)],
                tables("manhua_series", None, None),
                [(8, "甲壳虫")],
                douyins,
                [4, 6],
                accounts,
            ]
        )
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_task(session, write_body(title_ids=[], batch_titles=[]), 3))
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(caught.exception.message, "视频素材表不存在")
        self.assertFalse(any(isinstance(row, UniNativeTask) for row in session.added))
        self.assertEqual(session.commits, 0)

    def test_missing_title_table_rejects_library_ids(self) -> None:
        """标题库不在时，不能引用标题 id。"""
        template, subject, douyins, accounts, *_rest = self._ready()
        session = FakeSession(
            [
                [(template, subject)],
                tables("manhua_series", None, None),
                [(8, "甲壳虫")],
                douyins,
                [4, 6],
                accounts,
            ]
        )
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_task(session, write_body(video_ids=[], batch_titles=[]), 3))
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(caught.exception.message, "标题库不存在")
        self.assertEqual(session.commits, 0)

    def test_batch_titles_save_when_the_library_is_absent(self) -> None:
        """临时标题不依赖标题库，也不会插进标题库。"""
        template, subject, douyins, accounts, *_rest = self._ready()
        session = FakeSession(
            [
                [(template, subject)],
                tables("manhua_series", None, None),
                [(8, "甲壳虫")],
                douyins,
                [4, 6],
                accounts,
            ]
        )
        item = asyncio.run(create_task(session, write_body(video_ids=[], title_ids=[]), 3))
        self.assertEqual(item["batch_titles"], ["临时标题"])
        self.assertEqual(item["titles"], [])
        self.assertFalse(any(isinstance(row, MaterialTitle) for row in session.added))

    def test_missing_series_table_does_not_invent_a_row(self) -> None:
        """短剧表不在库里就拒绝，不写短剧，也不写任务。"""
        template, subject, *_rest = self._ready()
        session = FakeSession([[(template, subject)], tables(None, None, None)])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_task(session, write_body(video_ids=[], title_ids=[], batch_titles=[]), 3))
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(caught.exception.message, "短剧库不存在")
        self.assertEqual(session.added, [])

    def test_missing_series_row_is_not_found(self) -> None:
        """短剧 id 没有对应的未删除行。"""
        template, subject, *_rest = self._ready()
        session = FakeSession([[(template, subject)], tables("manhua_series", None, None), []])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_task(session, write_body(video_ids=[], title_ids=[], batch_titles=[]), 3))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(caught.exception.message, "短剧不存在")
        self.assertEqual(session.commits, 0)

    def test_missing_template_is_not_found(self) -> None:
        """标准模板和已删模板都当不存在。"""
        session = FakeSession([[]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_task(session, write_body(), 3))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(caught.exception.message, "模板不存在")
        self.assertEqual(session.commits, 0)

    def test_standard_douyin_is_rejected(self) -> None:
        """标准号不能配进全域任务。"""
        template, subject, _douyins, *_rest = self._ready()
        session = FakeSession(
            [
                [(template, subject)],
                tables("manhua_series", None, None),
                [(8, "甲壳虫")],
                [make_douyin(delivery_mode="standard")],
            ]
        )
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_task(session, write_body(video_ids=[], title_ids=[], batch_titles=[], accounts=[{"douyin_account_id": 4, "advertiser_id": 90001}]), 3))
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(caught.exception.message, "只能使用全域抖音号")
        self.assertEqual(session.commits, 0)

    def test_douyin_must_belong_to_the_pitcher(self) -> None:
        """没分给当前投手的全域号不能用。"""
        template, subject, douyins, *_rest = self._ready()
        session = FakeSession(
            [
                [(template, subject)],
                tables("manhua_series", None, None),
                [(8, "甲壳虫")],
                [douyins[0]],
                [],
            ]
        )
        body = write_body(
            video_ids=[],
            title_ids=[],
            batch_titles=[],
            accounts=[{"douyin_account_id": 4, "advertiser_id": 90001}],
        )
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_task(session, body, 3))
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(caught.exception.message, "抖音号未分配给当前投手")

    def test_account_must_belong_to_the_pitcher(self) -> None:
        """账户必须是当前投手名下的有效户。"""
        template, subject, douyins, *_rest = self._ready()
        session = FakeSession(
            [
                [(template, subject)],
                tables("manhua_series", None, None),
                [(8, "甲壳虫")],
                [douyins[0]],
                [4],
                [],
            ]
        )
        body = write_body(
            video_ids=[],
            title_ids=[],
            batch_titles=[],
            accounts=[{"douyin_account_id": 4, "advertiser_id": 90001}],
        )
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_task(session, body, 3))
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(caught.exception.message, "账户不存在、未分配给当前投手或已失效")

    def test_update_replaces_children_and_stays_saved(self) -> None:
        """整表更新换掉临时标题，状态仍是 saved，执行时间仍为空。"""
        template, subject, douyins, accounts, *_rest = self._ready()
        current = make_task()
        session = FakeSession(
            [
                tables("manhua_series", None, None),
                [(current, template, "甲壳虫")],
                [(template, subject)],
                [(8, "甲壳虫")],
                [douyins[0]],
                [4],
                [accounts[0]],
            ]
        )
        body = write_body(
            project_budget="70",
            video_ids=[],
            title_ids=[],
            batch_titles=["新临时"],
            accounts=[{"douyin_account_id": 4, "advertiser_id": 90001}],
            promotion_links=[],
        )
        item = asyncio.run(update_task(session, 40, body, 3))
        self.assertEqual(item["project_budget"], "70.00")
        self.assertEqual(item["status"], "saved")
        self.assertIsNone(item["executed_at"])
        self.assertEqual(item["batch_titles"], ["新临时"])
        deletes = " ".join(str(statement) for statement in session.statements)
        self.assertIn("uni_native_task_batch_title", deletes)
        self.assertTrue(any(isinstance(row, UniNativeTaskBatchTitle) and row.title == "新临时" for row in session.added))
        self.assertEqual(current.status, "saved")
        self.assertIsNone(current.executed_at)
        self.assertEqual(session.commits, 1)

    def test_delete_is_soft_and_hidden_from_others(self) -> None:
        """软删自己的任务。别人的 id 当不存在，不会被删。"""
        current = make_task()
        session = FakeSession([tables("manhua_series", None, None), [(current, make_template(), "甲壳虫")]])
        item = asyncio.run(delete_task(session, 40, 3))
        self.assertEqual(item, {"id": "40", "deleted": True})
        self.assertEqual(current.is_deleted, 1)
        self.assertIsNotNone(current.deleted_at)
        missing = FakeSession([tables("manhua_series", None, None), []])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(delete_task(missing, 40, 9))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(caught.exception.message, "投放任务不存在")
        self.assertEqual(missing.commits, 0)

    def test_list_returns_saved_tasks_for_the_series_name(self) -> None:
        """列表带回剧名、简称、账户、推广链和临时标题。素材表不在就不去连。"""
        task = make_task()
        template = make_template()
        account = UniNativeTaskAccount(task_id=40, douyin_account_id=4, advertiser_account_id=31, sort_order=0)
        account.id = 1
        link = UniNativeTaskLink(task_id=40, charge_mode="IAA", link_text="https://iaa.example/a", sort_order=0)
        link.id = 2
        session = FakeSession(
            [
                tables("manhua_series", None, None),
                [1],
                [(task, template, "甲壳虫")],
                [(account, make_douyin(), make_advertiser())],
                [link],
                [],
            ]
        )
        page = asyncio.run(
            list_tasks(session, TaskQuery(date_start=date(2026, 9, 1), series_name="甲"), 3)
        )
        self.assertEqual(page["total"], 1)
        item = page["list"][0]
        self.assertEqual(item["status"], "saved")
        self.assertIsNone(item["executed_at"])
        self.assertEqual(item["series_short_name"], "甲壳")
        self.assertEqual(item["accounts"][0]["aweme_id"], "aweme-u")
        self.assertEqual(item["promotion_links"][0]["link_text"], "https://iaa.example/a")
        self.assertEqual(item["videos"], [])
        self.assertEqual(item["titles"], [])

    def test_series_name_filter_is_empty_when_the_series_table_is_absent(self) -> None:
        """剧名筛选依赖短剧表。表不在就返回空页，不去查任务。"""
        session = FakeSession([tables(None, None, None), [9]])
        page = asyncio.run(list_tasks(session, TaskQuery(series_name="甲"), 3))
        self.assertEqual(page["list"], [])
        self.assertEqual(page["total"], 0)
        self.assertEqual(session.results, [[9]])

    def test_get_hides_another_pitchers_task(self) -> None:
        """详情只取自己的。没有行就是 404。"""
        session = FakeSession([tables("manhua_series", None, None), []])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(get_task(session, 40, 3))
        self.assertEqual(caught.exception.status_code, 404)


class HttpTests(unittest.TestCase):
    def test_login_is_required(self) -> None:
        """未登录不能看任务。"""
        client = http_client(FakeSession(), login=False)
        res = client.get(PREFIX)
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["code"], 401)
        self.assertEqual(res.json()["message"], "未带或 Token 无效")

    def test_create_returns_the_envelope(self) -> None:
        """新增走统一信封，成功是 HTTP 200。"""
        template, subject, douyins, accounts, video, title = SaveTests()._ready()
        session = FakeSession(
            [
                [(template, subject)],
                tables("manhua_series", "material_videos", "material_titles"),
                [(8, "甲壳虫")],
                douyins,
                [4, 6],
                accounts,
                [video],
                [title],
            ]
        )
        res = http_client(session).post(PREFIX, json=payload())
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["code"], 200)
        self.assertEqual(body["message"], "成功")
        self.assertEqual(body["data"]["status"], "saved")
        self.assertEqual(body["data"]["series_short_name"], "甲壳")
        self.assertIsNone(body["data"]["executed_at"])
        self.assertFalse(any(isinstance(row, MaterialTitle) for row in session.added))

    def test_status_cannot_be_sent_by_the_client(self) -> None:
        """状态不收。客户端不能写成执行中或完成。"""
        client = http_client(FakeSession())
        data = payload()
        data["status"] = "done"
        res = client.post(PREFIX, json=data)
        self.assertEqual(res.status_code, 422)
        self.assertIn("status", res.json()["message"])

    def test_list_uses_the_page_envelope(self) -> None:
        """列表字段叫 list，空关联也给空数组。"""
        task = make_task()
        session = FakeSession(
            [
                tables("manhua_series", None, None),
                [1],
                [(task, make_template(), "甲壳虫")],
                [],
                [],
                [],
            ]
        )
        res = http_client(session).get(PREFIX, params={"series_name": "甲", "date_start": "2026-09-01", "date_end": "2026-09-30"})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["code"], 200)
        self.assertEqual(body["data"]["total"], 1)
        self.assertEqual(body["data"]["page"], 1)
        self.assertEqual(body["data"]["list"][0]["status"], "saved")
        self.assertEqual(body["data"]["list"][0]["series_short_name"], "甲壳")


if __name__ == "__main__":
    unittest.main()
