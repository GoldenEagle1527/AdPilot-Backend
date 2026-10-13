"""全域端原生确认提交：一对一账户、假客户端发号。完成只表示假客户端结束。"""

from __future__ import annotations

import asyncio
import json
import unittest
from decimal import Decimal
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth import require_token
from app.core.db import get_session
from app.core.envelope import ApiError, register_exception_handlers
from app.modules.account.model import OeVideo, ProductLibrary
from app.modules.material_title.model import MaterialTitle
from app.modules.oceanengine.runtime import install_ocean_client
from app.modules.uni_native_task.controller import router
from app.modules.uni_native_task.model import UniNativeTaskAccount, UniNativeTaskLink
from app.modules.uni_native_task.schema import TaskWrite
from app.modules.uni_native_task.service import resolve_links
from app.modules.uni_native_task.submit import submit_loaded, submit_task
from tests.modules.standard_delivery.test_submit import Port, Sess
from tests.modules.uni_native_task.test_tasks import (
    FakeSession,
    make_advertiser,
    make_douyin,
    make_subject,
    make_task,
    make_template,
    make_video,
    tables,
    write_body,
)


def _library() -> ProductLibrary:
    row = ProductLibrary(
        name="视频库",
        library_no=77001,
        library_kind="video",
        organization_id=1,
        library_role="fallback",
        uploaded_count=0,
    )
    row.id = 6
    return row


def _title(text: str = "标题正好五字") -> MaterialTitle:
    row = MaterialTitle(title=text, category="common", uploader_id=3)
    row.id = 21
    return row


def _theater_link(
    link_id: int,
    name: str,
    url: str,
    media: int,
    *,
    enabled: bool = True,
    deleted: int = 0,
):
    """造一条剧场推广链。排序和收费模式由被测函数决定。"""
    from app.modules.theater.model import TheaterPromotionLink

    row = TheaterPromotionLink(
        series_id=8,
        promotion_url=url,
        recharge_template_name=name,
        media_config_type=media,
        is_enabled=enabled,
    )
    row.id = link_id
    row.is_deleted = deleted
    return row


class LinkFillTests(unittest.TestCase):
    def test_omitted_links_bring_every_enabled_tier(self) -> None:
        """没传链接时，这部剧启用的推广链全部带出。同一档位多条都留，空链接不要。"""
        from sqlalchemy.dialects import postgresql

        from app.modules.theater.lookup import enabled_series_links_stmt

        rows = [
            _theater_link(1, "超超小额", "https://x/tiny", 2),
            _theater_link(2, "小额", "https://x/small", 2),
            _theater_link(3, "自定义", "https://x/other", 0),
            _theater_link(9, "IAA", "https://x/iaa", 2),
            _theater_link(4, "中额", "https://x/mid", 3),
            _theater_link(8, "中额", "https://x/mid2", 2),
            _theater_link(5, "超小额", "https://x/smaller", 2),
            _theater_link(6, "小额", "", 2),
            _theater_link(7, "小额", "   ", 2),
            _theater_link(10, "IAA", "https://x/off", 3, enabled=False),
            _theater_link(11, "小额", "https://x/gone", 2, deleted=1),
        ]
        session = FakeSession([rows])
        links = asyncio.run(resolve_links(session, write_body(promotion_links=[]), 8))
        self.assertEqual(
            links,
            [
                ("IAA", "https://x/iaa", "IAA"),
                ("IAA", "https://x/mid", "中额"),
                ("IAP", "https://x/mid2", "中额"),
                ("IAP", "https://x/small", "小额"),
                ("IAP", "https://x/smaller", "超小额"),
                ("IAP", "https://x/tiny", "超超小额"),
                ("IAP", "https://x/other", "自定义"),
            ],
        )
        self.assertEqual(len(session.statements), 1)
        sql = str(
            enabled_series_links_stmt(8).compile(
                dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
            )
        )
        self.assertIn("theater_promotion_links.series_id = 8", sql)
        self.assertIn("theater_promotion_links.is_deleted = 0", sql)
        self.assertIn("theater_promotion_links.is_enabled IS true", sql)
        self.assertNotIn("LIMIT", sql)
        absent = FakeSession([[]])
        self.assertEqual(asyncio.run(resolve_links(absent, write_body(promotion_links=[]), 8)), [])

    def test_client_links_are_kept_and_skip_the_theater_table(self) -> None:
        """客户端传了文本就按原文保存，不再查剧场。档位名不传就是空。"""
        session = FakeSession()
        body = write_body(
            promotion_links=[
                {
                    "charge_mode": "IAP",
                    "link_text": "https://hand.example/x",
                    "recharge_template_name": "手填档",
                },
                {"charge_mode": "IAA", "link_text": "https://iaa.example/a"},
            ]
        )
        links = asyncio.run(resolve_links(session, body, 8))
        self.assertEqual(session.statements, [])
        self.assertEqual(
            links,
            [
                ("IAP", "https://hand.example/x", "手填档"),
                ("IAA", "https://iaa.example/a", ""),
            ],
        )


class SubmitTests(unittest.TestCase):
    def tearDown(self) -> None:
        install_ocean_client(None)

    def test_one_douyin_per_account_and_fake_client_finishes(self) -> None:
        """每个账户一行一个项目、一条广告。执行中是 running，结束后是 done。素材不算巨量已上传。"""
        port = Port()
        seen: list[str] = []
        create_project = port.create_project

        async def _watch(token: str, body: dict) -> dict:
            seen.append(task.status)
            return await create_project(token, body)

        port.create_project = _watch
        install_ocean_client(port)
        task = make_task()
        template = make_template()
        subject = make_subject()
        library = _library()
        session = Sess(subject, library)
        link = UniNativeTaskLink(
            task_id=40, charge_mode="IAA", link_text="https://iaa.example/from-theater", sort_order=0
        )
        result = asyncio.run(
            submit_loaded(
                session,
                task,
                template,
                subject,
                "甲壳虫",
                [
                    (make_douyin(id=4, aweme_id="aweme-a"), make_advertiser(id=31, advertiser_id=90001)),
                    (make_douyin(id=6, aweme_id="aweme-b"), make_advertiser(id=32, advertiser_id=90002)),
                ],
                [link],
                [make_video()],
                [_title()],
                [],
                library,
            )
        )
        self.assertEqual(seen, ["running", "running"])
        self.assertEqual(task.status, "done")
        self.assertIsNotNone(task.executed_at)
        self.assertEqual(template.delivery_mode, "uni")
        self.assertTrue(result["materials_uploaded"])
        self.assertEqual(result["status"], "done")
        self.assertNotEqual(result["status"], "完成")
        self.assertEqual(result["promotion_links"][0]["link_text"], "https://iaa.example/from-theater")
        self.assertEqual(len(result["accounts"]), 2)
        self.assertEqual([item["aweme_id"] for item in result["accounts"]], ["aweme-a", "aweme-b"])
        self.assertEqual(len(result["accounts"][0]["promotions"]), 1)
        self.assertEqual(result["accounts"][0]["project_id"], 8800000000000001)
        self.assertEqual(result["accounts"][1]["project_id"], 8800000000000002)
        self.assertEqual(result["accounts"][0]["image_id"], "img-from-client-1")
        self.assertNotIn("image_file", port.images[0])
        self.assertGreater(port.videos, 0)
        project = result["accounts"][0]["project"]
        self.assertEqual(project["delivery_mode"], "MANUAL")
        self.assertEqual(project["audience"], {"district": "NONE"})
        self.assertEqual(project["native_setting"]["aweme_id"], "aweme-a")
        self.assertEqual(project["delivery_setting"]["roi_goal"], 1.2)
        promo = json.dumps(result["accounts"][0]["promotions"], ensure_ascii=False)
        self.assertIn("https://iaa.example/from-theater", promo)
        self.assertNotIn("video_id", promo)
        self.assertIn("15", promo)
        self.assertNotEqual(result["status"], "完成")

    def _submit(self, template: Any) -> tuple[Port, dict[str, Any]]:
        port = Port()
        install_ocean_client(port)
        library = _library()
        result = asyncio.run(
            submit_loaded(
                Sess(make_subject(), library),
                make_task(),
                template,
                make_subject(),
                "甲壳虫",
                [(make_douyin(), make_advertiser())],
                [],
                [make_video()],
                [_title()],
                [],
                library,
            )
        )
        return port, result

    def test_saved_schedule_product_and_aigc_reach_the_bodies(self) -> None:
        """起止日期、时段、产品名称、卖点、行动号召和 AIGC 开关都按模板带上。商品仍用剧名。"""
        from datetime import date

        template = make_template()
        template.schedule_type = "SCHEDULE_START_END"
        template.schedule_start_date = date(2026, 10, 20)
        template.schedule_end_date = date(2026, 10, 31)
        template.schedule_time = "1" * 336
        template.product_name = "产品甲"
        template.selling_points = ["这是产品卖点"]
        template.call_to_action_buttons = ["立即观看"]
        port, result = self._submit(template)
        project = result["accounts"][0]["project"]
        setting = project["delivery_setting"]
        self.assertEqual(setting["schedule_type"], "SCHEDULE_START_END")
        self.assertEqual(setting["start_time"], "2026-10-20")
        self.assertEqual(setting["end_time"], "2026-10-31")
        self.assertEqual(setting["schedule_time"], "1" * 336)
        self.assertEqual(setting["budget_mode"], "BUDGET_MODE_DAY")
        self.assertEqual(setting["budget"], float(make_task().project_budget))
        self.assertEqual(setting["roi_goal"], float(make_task().roi_coefficient))
        self.assertNotIn("deep_bid_type", setting)
        self.assertEqual(project["aigc_dynamic_creative_switch"], "ON")
        self.assertEqual(port.projects[0]["template"]["aigc_dynamic_creative_switch"], "ON")
        from app.modules.oceanengine.delivery import _project_remote_body
        from app.modules.oceanengine.schema import ProjectCreate

        remote = _project_remote_body(ProjectCreate(**port.projects[0]))
        self.assertEqual(remote["aigc_dynamic_creative_switch"], "ON")
        self.assertEqual(remote["delivery_setting"]["schedule_type"], "SCHEDULE_START_END")
        self.assertEqual(project["delivery_range"], {"inventory_catalog": "UNIVERSAL_SMART"})
        materials = result["accounts"][0]["promotions"][0]["promotion_materials"]
        self.assertEqual(materials["product_info"]["titles"], ["产品甲"])
        self.assertEqual(materials["product_info"]["selling_points"], ["这是产品卖点"])
        self.assertEqual(materials["call_to_action_buttons"], ["立即观看"])
        self.assertNotIn("source", result["accounts"][0]["promotions"][0])
        self.assertEqual(port.products[0]["book_name"], "甲壳虫")

    def test_unset_schedule_and_product_name_are_left_out(self) -> None:
        """从今天起不带起止日期，时段不限不传。没填产品名称不拿剧名顶上。AIGC 关就传 OFF。"""
        template = make_template()
        template.schedule_type = "SCHEDULE_FROM_NOW"
        template.aigc_dynamic_creative = False
        _port, result = self._submit(template)
        project = result["accounts"][0]["project"]
        setting = project["delivery_setting"]
        self.assertEqual(setting["schedule_type"], "SCHEDULE_FROM_NOW")
        self.assertNotIn("start_time", setting)
        self.assertNotIn("end_time", setting)
        self.assertNotIn("schedule_time", setting)
        self.assertEqual(project["aigc_dynamic_creative_switch"], "OFF")
        info = result["accounts"][0]["promotions"][0]["promotion_materials"]["product_info"]
        self.assertNotIn("titles", info)
        self.assertEqual(info["selling_points"], [])

    def test_short_title_rejects_the_whole_submit(self) -> None:
        """标题长度不对就整单拒绝，不调用客户端。"""
        port = Port()
        install_ocean_client(port)
        with self.assertRaises(ApiError) as caught:
            asyncio.run(
                submit_loaded(
                    Sess(make_subject(), _library()),
                    make_task(),
                    make_template(),
                    make_subject(),
                    "甲壳虫",
                    [(make_douyin(), make_advertiser())],
                    [],
                    [],
                    [_title("短")],
                    [],
                    _library(),
                )
            )
        self.assertEqual(caught.exception.message, "标题长度须为 5–55 个字")
        self.assertEqual(port.projects, [])

    def test_done_submit_writes_the_ocean_project_id(self) -> None:
        """每个账户建出一个项目、一条广告，两个编号都写回这一行，和完成状态一起留下。"""
        port = Port()
        install_ocean_client(port)
        row = UniNativeTaskAccount(task_id=40, douyin_account_id=4, advertiser_account_id=31, sort_order=0)
        row.id = 1
        task = make_task()
        library = _library()
        result = asyncio.run(
            submit_loaded(
                Sess(make_subject(), library),
                task,
                make_template(),
                make_subject(),
                "甲壳虫",
                [(row, make_douyin(), make_advertiser())],
                [],
                [make_video()],
                [_title()],
                [],
                library,
            )
        )
        self.assertEqual(task.status, "done")
        self.assertEqual(row.ocean_project_id, 8800000000000001)
        self.assertEqual(row.ocean_project_id, result["accounts"][0]["project_id"])
        self.assertEqual(len(port.projects), 1)
        self.assertEqual(row.ocean_promotion_id, 9100000000000001)
        self.assertEqual(row.ocean_promotion_id, result["accounts"][0]["promotions"][0]["promotion_id"])

    def test_failed_submit_keeps_project_ids_already_created(self) -> None:
        """后面的账户创建失败时，前面已经建出的巨量项目 id 留在账户行上，任务标失败。"""
        port = Port()
        create_project = port.create_project

        async def _project(token: str, body: dict[str, Any]) -> dict[str, Any]:
            if body.get("advertiser_id") == 90002:
                raise ApiError(502, "创建项目失败")
            return await create_project(token, body)

        port.create_project = _project
        install_ocean_client(port)
        first = UniNativeTaskAccount(task_id=40, douyin_account_id=4, advertiser_account_id=31, sort_order=0)
        second = UniNativeTaskAccount(task_id=40, douyin_account_id=6, advertiser_account_id=32, sort_order=1)
        first.id = 1
        second.id = 2
        task = make_task()
        library = _library()
        with self.assertRaises(ApiError) as caught:
            asyncio.run(
                submit_loaded(
                    Sess(make_subject(), library),
                    task,
                    make_template(),
                    make_subject(),
                    "甲壳虫",
                    [
                        (first, make_douyin(id=4, aweme_id="aweme-a"), make_advertiser(id=31, advertiser_id=90001)),
                        (second, make_douyin(id=6, aweme_id="aweme-b"), make_advertiser(id=32, advertiser_id=90002)),
                    ],
                    [],
                    [make_video()],
                    [_title()],
                    [],
                    library,
                )
            )
        self.assertEqual(caught.exception.status_code, 502)
        self.assertEqual(caught.exception.message, "创建项目失败")
        self.assertEqual(task.status, "failed")
        self.assertEqual(task.failure_reason, "创建项目失败")
        self.assertEqual(first.ocean_project_id, 8800000000000001)
        self.assertIsNone(second.ocean_project_id)

    def test_submit_refuses_when_the_task_already_left_saved(self) -> None:
        """running、done、failed 再提交是 409，不再调客户端建项目。"""
        for status in ("running", "done", "failed"):
            task = make_task()
            task.status = status
            port = Port()
            install_ocean_client(port)
            session = FakeSession(
                [tables("manhua_series", None, None), [(task, make_template(), "甲壳虫", "番茄")]]
            )
            with self.assertRaises(ApiError) as caught:
                asyncio.run(submit_task(session, 40, 3))
            self.assertEqual(caught.exception.status_code, 409)
            self.assertEqual(caught.exception.message, "任务已提交，不能重复创建项目")
            self.assertEqual(port.projects, [])
            self.assertEqual(task.status, status)


class HttpTests(unittest.TestCase):
    def _client(self, session: Any, *, login: bool = True) -> TestClient:
        app = FastAPI()
        register_exception_handlers(app)
        app.include_router(router)

        async def _yield():
            yield session

        app.dependency_overrides[get_session] = _yield
        if login:
            app.dependency_overrides[require_token] = lambda: {
                "id": "3",
                "nickname": "投手",
                "login_account": "pitcher",
                "tenant": "agent",
                "enabled": True,
                "menu_ids": ["56"],
                "data_scope": {"self_only": True, "department_ids": []},
            }
        return TestClient(app)

    def test_login_is_required_and_missing_task_is_404(self) -> None:
        """未登录 401。别人的或没有的任务 404，状态不会被写成完成。"""
        guest = self._client(FakeSession(), login=False)
        missing = guest.post("/api/v1/uni-native-tasks/40/submit")
        self.assertEqual(missing.status_code, 401)
        hidden = self._client(FakeSession([tables("manhua_series", None, None), []])).post(
            "/api/v1/uni-native-tasks/40/submit"
        )
        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(hidden.json()["message"], "投放任务不存在")


class BodyGuardTests(unittest.TestCase):
    def test_task_write_still_accepts_client_link_text(self) -> None:
        """客户端可以自己带 link_text。空列表留给剧场补。"""
        body = TaskWrite(**write_body().model_dump())
        self.assertEqual(body.promotion_links[0].link_text, "https://iaa.example/a")
        empty = write_body(promotion_links=[])
        self.assertEqual(empty.promotion_links, [])
        self.assertIsInstance(empty.roi_coefficient, Decimal | type(None))
