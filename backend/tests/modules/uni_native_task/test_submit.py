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
from app.modules.uni_native_task.model import UniNativeTaskLink
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


class LinkFillTests(unittest.TestCase):
    def test_omitted_links_use_the_series_iaa_url(self) -> None:
        """客户端不传链接时，用这部剧的 IAA 推广链。表不在就保持空。"""
        filled = FakeSession(
            [[("theater_promotion_links",)], [("https://iaa.example/from-theater",)], [(None,)]]
        )
        links = asyncio.run(resolve_links(filled, write_body(promotion_links=[]), 8))
        self.assertEqual(links, [("IAA", "https://iaa.example/from-theater")])
        absent = FakeSession([[(None,)], [(None,)]])
        self.assertEqual(asyncio.run(resolve_links(absent, write_body(promotion_links=[]), 8)), [])

    def test_client_links_are_kept_and_skip_the_theater_table(self) -> None:
        """客户端传了文本就按原文保存，不再查剧场。"""
        session = FakeSession()
        body = write_body()
        links = asyncio.run(resolve_links(session, body, 8))
        self.assertEqual(session.statements, [])
        self.assertEqual(links[0], ("IAA", body.promotion_links[0].link_text))


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
