"""标准投放确认提交：切片、报文、假客户端发号，以及假数据不进业务代码。"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth import require_token
from app.core.db import get_session
from app.core.envelope import ApiError, register_exception_handlers
from app.core.times import BEIJING
from app.modules.account.model import AdvertiserAccount, DeliverySubject, DouyinAccount, OeVideo, ProductLibrary
from app.modules.material_title.model import MaterialTitle
from app.modules.material_video.model import MaterialVideo
from app.modules.oceanengine.runtime import install_ocean_client
from app.modules.standard_delivery.controller import router
from app.modules.standard_delivery.crud import SeriesBrief
from app.modules.standard_delivery.model import DeliveryTaskDraft, DeliveryTemplate
from app.modules.standard_delivery.submit import slice_materials, submit_draft, submit_loaded

BACKEND = Path(__file__).resolve().parents[3]
CREATED = datetime(2026, 10, 8, 6, 0, tzinfo=BEIJING)


class Port:
    """不发 HTTP。项目号和商品号由测试指定，避免和序列起点撞车。"""

    requires_stored_token = False

    def __init__(self) -> None:
        self.projects: list[dict[str, Any]] = []
        self.products: list[dict[str, Any]] = []
        self.images: list[dict[str, Any]] = []
        self.videos = 0
        self._project = 8800000000000000
        self._product = 4241
        self._image = 0

    async def create_project(self, _token: str, body: dict[str, Any]) -> dict[str, Any]:
        """记下正文并回一个项目号。"""
        self.projects.append(body)
        self._project += 1
        return {"data": {"project_id": self._project}}

    async def upload_product(self, _token: str, body: dict[str, Any]) -> dict[str, Any]:
        """记下正文并回一个商品号。"""
        self.products.append(body)
        self._product += 1
        return {"data": {"product_id": self._product}}

    async def upload_image(self, _token: str, body: dict[str, Any]) -> dict[str, Any]:
        """不读文件，回一个图片号。"""
        self.images.append(body)
        self._image += 1
        return {"data": {"id": f"img-from-client-{self._image}"}}

    async def upload_video(self, _token: str, body: dict[str, Any]) -> dict[str, Any]:
        """提交不该走到这里。"""
        self.videos += 1
        return {"data": {"video_id": "unused"}}


class Sess:
    """只实现建项目和上传商品用到的会话方法。"""

    def __init__(self, subject: DeliverySubject, library: ProductLibrary) -> None:
        self.subject = subject
        self.library = library
        self.added: list[Any] = []
        self.commits = 0

    async def get(self, _model: Any, pk: int) -> DeliverySubject | None:
        """按主键交回主体。"""
        if pk == self.subject.id:
            return self.subject
        return None

    async def scalar(self, statement: Any) -> ProductLibrary | None:
        """商品上传按预置库返回。主体查询不把库交回去。"""
        if "product_library" not in str(statement):
            return None
        return self.library

    def add(self, row: Any) -> None:
        """记下待插入行。"""
        self.added.append(row)

    async def flush(self) -> None:
        """不落库。"""

    async def refresh(self, row: Any) -> None:
        """保持调用方已经写上的号。"""
        row.id = getattr(row, "id", None) or 1

    async def commit(self) -> None:
        """记一次提交。"""
        self.commits += 1


def _subject() -> DeliverySubject:
    row = DeliverySubject(
        name="甲主体",
        subject_no=100,
        delivery_mode="standard",
        theater_name="番茄",
        theater_kind="端原生",
        charge_mode="IAA",
        min_bid=Decimal("1.00"),
        max_bid=Decimal("2.00"),
        material_account_id=1,
        dual_bid=False,
    )
    row.id = 7
    row.is_deleted = 0
    return row


def _template(**kwargs: Any) -> DeliveryTemplate:
    row = DeliveryTemplate(
        name="免费模板",
        delivery_mode="standard",
        charge_mode=kwargs.get("charge_mode", "IAA"),
        subject_id=7,
        bid_panels=[],
        ads_per_account=kwargs.get("ads_per_account", 2),
        ocean_delivery_mode=kwargs.get("ocean_delivery_mode", "MANUAL"),
        bid_type="CUSTOM",
        schedule_type="SCHEDULE_FROM_NOW",
        ad_source="来源甲",
        product_name="产品甲",
        selling_points=["卖点一"],
        call_to_action_buttons=["立即观看"],
        roi_goal=kwargs.get("roi_goal", Decimal("1.500")),
        videos_per_ad=kwargs.get("videos_per_ad", 2),
        titles_per_ad=kwargs.get("titles_per_ad", 1),
    )
    row.id = 11
    return row


def _draft(**kwargs: Any) -> DeliveryTaskDraft:
    row = DeliveryTaskDraft(
        template_id=11,
        charge_mode=kwargs.get("charge_mode", "IAA"),
        pitcher_user_id=3,
        douyin_account_id=4,
        series_id=8,
        placement=kwargs.get("placement", "aweme_feed"),
        project_budget=Decimal("100.00"),
        ad_budget=Decimal("50.50"),
        optimize_goal=kwargs.get("optimize_goal", "AD_CONVERT_TYPE_ACTIVE"),
        product_library_id=6,
        album_url=kwargs.get("album_url", "https://album.example/only"),
        project_operation="ENABLE",
        promotion_operation="DISABLE",
    )
    row.id = 40
    row.created_date = CREATED
    row.updated_date = CREATED
    return row


def _douyin() -> DouyinAccount:
    row = DouyinAccount(aweme_id="aweme-std", name="标准号", delivery_mode="standard", enabled=True)
    row.id = 4
    return row


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


def _account(advertiser_id: int, row_id: int) -> AdvertiserAccount:
    row = AdvertiserAccount(
        organization_id=1,
        oe_app_id=1,
        advertiser_id=advertiser_id,
        name=f"户{advertiser_id}",
        sync_status="active",
        pitcher_user_id=3,
    )
    row.id = row_id
    return row


def _video(row_id: int, kind: str = "vertical_video") -> MaterialVideo:
    row = MaterialVideo(
        name=f"视频{row_id}",
        material_type=kind,
        file_urls=["https://example.com/a.mp4"],
        series_id=8,
        platform="tomato",
        tag_id=1,
        ownership="private",
        uploader_id=3,
    )
    row.id = row_id
    return row


def _title(row_id: int, text: str) -> MaterialTitle:
    row = MaterialTitle(title=text, category="common", uploader_id=3)
    row.id = row_id
    return row


def _run(**kwargs: Any):
    """装上端口并提交一份内存草稿。"""
    port = Port()
    install_ocean_client(port)
    subject = _subject()
    library = _library()
    session = Sess(subject, library)
    template = kwargs.pop("template", _template())
    result = asyncio.run(
        submit_loaded(
            session,
            kwargs.pop("draft", _draft()),
            template,
            subject,
            _douyin(),
            SeriesBrief(8, "甲壳虫"),
            library,
            kwargs.pop("accounts", [_account(90001, 31), _account(90002, 32)]),
            kwargs.pop(
                "videos",
                [_video(1), _video(2), _video(3), _video(4, "horizontal_video"), _video(5)],
            ),
            kwargs.pop(
                "titles",
                [_title(21, "标题正好五字"), _title(22, "第二标题五字"), _title(23, "第三标题五字")],
            ),
        )
    )
    return port, session, template, result


class SliceTests(unittest.TestCase):
    def test_chunks_follow_saved_order_and_stop(self) -> None:
        """按顺序切。不够一整块就停，不把列表再转一圈。"""
        videos = [1, 2, 3, 4, 5]
        titles = ["a", "b", "c"]
        sliced = slice_materials(
            videos, titles, videos_per_ad=2, titles_per_ad=1, ads_per_account=2, account_count=2
        )
        self.assertEqual(sliced[0], [([1, 2], ["a"]), ([3, 4], ["b"])])
        self.assertEqual(sliced[1], [])
        self.assertNotIn(5, [item for chunk in sliced for videos, _titles in chunk for item in videos])


class SubmitTests(unittest.TestCase):
    def tearDown(self) -> None:
        install_ocean_client(None)

    def test_bodies_use_client_ids_and_slice_per_account(self) -> None:
        """项目号、商品号、主图号来自客户端。专辑链接只用草稿。地域不传城市。"""
        port, session, template, result = _run()
        self.assertEqual(template.delivery_mode, "standard")
        self.assertEqual(result["aweme_id"], "aweme-std")
        self.assertEqual(len(result["accounts"]), 2)
        first, second = result["accounts"]
        self.assertEqual(first["project_id"], 8800000000000001)
        self.assertEqual(second["project_id"], 8800000000000002)
        self.assertEqual(first["product_id"], 4242)
        self.assertEqual(first["image_id"], "img-from-client-1")
        self.assertNotIn("image_file", port.images[0])
        self.assertEqual(port.images[0]["upload_type"], "UPLOAD_BY_FILE")
        self.assertEqual(port.videos, 0)
        self.assertFalse(any(isinstance(row, OeVideo) for row in session.added))
        project = first["project"]
        self.assertEqual(project["delivery_mode"], "MANUAL")
        self.assertEqual(project["audience"], {"district": "NONE"})
        self.assertNotIn("city", project["audience"])
        self.assertNotIn("roi_goal", project["delivery_setting"])
        self.assertNotIn("roi_coefficient", project)
        self.assertEqual(project["delivery_range"]["inventory_type"], ["INVENTORY_AWEME_FEED", "INVENTORY_FEED"])
        self.assertEqual(project["related_product"]["product_id"], 4242)
        self.assertEqual(project["related_product"]["product_platform_id"], 77001)
        self.assertNotIn("asset_ids", project["optimize_goal"])
        self.assertEqual(len(first["promotions"]), 2)
        self.assertEqual(second["promotions"], [])
        promo = first["promotions"][0]
        self.assertEqual(promo["project_id"], first["project_id"])
        materials = promo["promotion_materials"]
        self.assertEqual(materials["playlet_series_url_list"], ["https://album.example/only"])
        self.assertEqual(materials["video_material_list"][0]["material_id"], 1)
        self.assertNotIn("video_id", materials["video_material_list"][0])
        self.assertEqual(materials["video_material_list"][0]["image_mode"], "CREATIVE_IMAGE_MODE_VIDEO_VERTICAL")
        self.assertEqual(materials["title_material_list"], [{"title": "标题正好五字"}])
        self.assertEqual(promo["roi_goal"], 1.5)
        self.assertEqual(first["promotions"][1]["promotion_materials"]["video_material_list"][0]["material_id"], 3)
        horizontal = first["promotions"][1]["promotion_materials"]["video_material_list"]
        self.assertEqual(horizontal[1]["image_mode"], "CREATIVE_IMAGE_MODE_VIDEO")
        self.assertTrue(project["name"].startswith("甲壳NB"))
        self.assertEqual(session.commits, 1)

    def test_manual_video_cap_rejects_the_whole_submit(self) -> None:
        """手动投放每个广告超过 10 个视频，整单拒绝，不调用客户端。"""
        port = Port()
        install_ocean_client(port)
        with self.assertRaises(ApiError) as caught:
            asyncio.run(
                submit_loaded(
                    Sess(_subject(), _library()),
                    _draft(),
                    _template(videos_per_ad=11),
                    _subject(),
                    _douyin(),
                    SeriesBrief(8, "甲壳虫"),
                    _library(),
                    [_account(90001, 31)],
                    [_video(index) for index in range(1, 12)],
                    [_title(21, "标题正好五字")],
                )
            )
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(caught.exception.message, "手动投放每个广告最多 10 个视频")
        self.assertEqual(port.projects, [])

    def test_bad_title_length_rejects_before_any_client_call(self) -> None:
        """切进广告的标题不在 5–30 字，整单失败，不截断、不跳过。"""
        port = Port()
        install_ocean_client(port)
        with self.assertRaises(ApiError) as caught:
            asyncio.run(
                submit_loaded(
                    Sess(_subject(), _library()),
                    _draft(),
                    _template(videos_per_ad=1, titles_per_ad=2, ads_per_account=1),
                    _subject(),
                    _douyin(),
                    SeriesBrief(8, "甲壳虫"),
                    _library(),
                    [_account(90001, 31)],
                    [_video(1)],
                    [_title(21, "标题正好五字"), _title(22, "短")],
                )
            )
        self.assertEqual(caught.exception.message, "标题长度须为 5–30 个字")
        self.assertEqual(port.projects, [])
        self.assertEqual(port.products, [])
        self.assertEqual(port.images, [])

    def test_procedural_paid_puts_roi_on_the_project(self) -> None:
        """付费自动投放的 ROI 在项目上，广告上不再放一份。"""
        _port, _session, template, result = _run(
            template=_template(
                charge_mode="IAP",
                ocean_delivery_mode="PROCEDURAL",
                videos_per_ad=1,
                titles_per_ad=1,
                ads_per_account=1,
                roi_goal=Decimal("2.500"),
            ),
            draft=_draft(charge_mode="IAP", optimize_goal="AD_CONVERT_TYPE_PAY"),
            accounts=[_account(90001, 31)],
            videos=[_video(1)],
            titles=[_title(21, "标题正好五字")],
        )
        project = result["accounts"][0]["project"]
        self.assertEqual(template.delivery_mode, "standard")
        self.assertEqual(project["delivery_mode"], "PROCEDURAL")
        self.assertEqual(project["delivery_setting"]["roi_goal"], 2.5)
        self.assertEqual(project["delivery_setting"]["deep_bid_type"], "ROI_COEFFICIENT")
        self.assertEqual(project["optimize_goal"]["deep_external_action"], "AD_CONVERT_TYPE_PURCHASE_ROI")
        self.assertNotIn("roi_goal", result["accounts"][0]["promotions"][0])
        self.assertNotIn("roi_coefficient", project)

    def test_does_not_cycle_when_the_next_ad_runs_out(self) -> None:
        """下一条广告不够一整块时停，不把已经用过的视频再塞回去。"""
        _port, _session, _template_row, result = _run(
            template=_template(videos_per_ad=2, titles_per_ad=1, ads_per_account=2),
            accounts=[_account(90001, 31)],
            videos=[_video(1), _video(2)],
            titles=[_title(21, "标题正好五字"), _title(22, "第二标题五字")],
        )
        self.assertEqual(len(result["accounts"][0]["promotions"]), 1)


class HttpTests(unittest.TestCase):
    def tearDown(self) -> None:
        install_ocean_client(None)

    def _client(self, session: Any, *, login: bool = True, menus: list[str] | None = None) -> TestClient:
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
                "enabled": True,
                "menu_ids": ["39", "46"] if menus is None else menus,
            }
        return TestClient(app)

    def test_login_and_menu_and_owner(self) -> None:
        """未登录 401。没有草稿菜单 403。不是自己的草稿 404。"""

        class Empty:
            async def execute(self, _statement: Any) -> Any:
                return type("R", (), {"one_or_none": lambda self: None})()

        guest = self._client(Empty(), login=False)
        missing = guest.post("/api/v1/standard-delivery/task-drafts/40/submit")
        self.assertEqual(missing.status_code, 401)
        forbidden = self._client(Empty(), menus=["45"]).post("/api/v1/standard-delivery/task-drafts/40/submit")
        self.assertEqual(forbidden.status_code, 403)
        hidden = self._client(Empty()).post("/api/v1/standard-delivery/task-drafts/40/submit")
        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(hidden.json()["message"], "投放草稿不存在")


class IsolationTests(unittest.TestCase):
    def test_handlers_do_not_embed_fake_rows(self) -> None:
        """请求处理和投放服务不写假行、假号，也不引用测试目录。"""
        banned = ("fake_catalog", "9101", "9102", "7000000000000001", "local-", "api.oceanengine.com")
        roots = [
            BACKEND / "app" / "modules" / "standard_delivery",
            BACKEND / "app" / "modules" / "uni_native_task",
            BACKEND / "main.py",
        ]
        files: list[Path] = []
        for root in roots:
            files.extend(root.rglob("*.py") if root.is_dir() else [root])
        for path in files:
            text = path.read_text(encoding="utf-8")
            for token in banned:
                self.assertNotIn(token, text, f"{path.name} 含 {token}")
            self.assertNotIn("if mock", text, path.name)
