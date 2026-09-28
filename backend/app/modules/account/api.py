"""账户管理 HTTP。挂在 /api/v1/oceanengine，不另开前缀。"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.core.envelope import Envelope, success
from app.core.pagination import PageData
from app.modules.account import commands
from app.modules.account.schemas import (
    AssignAdvertisersBody,
    AssignPitchersBody,
    DouyinAssignData,
    DouyinBody,
    DouyinEnabledBody,
    DouyinEnabledData,
    DouyinItem,
    DouyinQuery,
    DouyinReclaimData,
    DouyinUpdateBody,
    ImportAdvertisersData,
    ProductLibraryAssignData,
    ProductLibraryBody,
    ProductLibraryItem,
    ProductLibraryQuery,
    RenameAdvertiserList,
    RenameAdvertisersBody,
    SubjectBody,
    SubjectItem,
    SubjectQuery,
    SyncAdvertisersData,
    SyncAdvertisersQuery,
    UnbindAdvertisersBody,
)
from app.modules.system_admin.deps import SessionDep, require_menu

router = APIRouter()

Menu63 = Annotated[dict[str, Any], Depends(require_menu("63"))]
Menu65 = Annotated[dict[str, Any], Depends(require_menu("65"))]
Menu66 = Annotated[dict[str, Any], Depends(require_menu("66"))]
Menu66or67 = Annotated[dict[str, Any], Depends(require_menu("67", "66"))]
Menu68 = Annotated[dict[str, Any], Depends(require_menu("68"))]
Menu64 = Annotated[dict[str, Any], Depends(require_menu("64"))]


def _operator(principal: dict[str, Any]) -> str:
    return str(principal["login_account"])


@router.post(
    "/advertisers/assign",
    response_model=Envelope[dict[str, Any]],
    summary="分配广告主投手",
)
async def post_assign_advertisers(
    session: SessionDep,
    principal: Menu63,
    body: AssignAdvertisersBody,
) -> dict[str, Any]:
    """任一户已有投手则整批拒绝。"""
    data = await commands.assign_advertisers(
        session, body.advertiser_ids, body.pitcher_user_id, _operator(principal)
    )
    return success(data)


@router.post(
    "/advertisers/rename",
    response_model=Envelope[RenameAdvertiserList],
    summary="批量改广告主本地名",
)
async def post_rename_advertisers(
    session: SessionDep,
    principal: Menu63,
    body: RenameAdvertisersBody,
) -> dict[str, Any]:
    """写本地展示名和改名审计。"""
    data = await commands.rename_advertisers(session, body.items, _operator(principal))
    return success(data)


@router.post(
    "/advertisers/unbind",
    response_model=Envelope[None],
    summary="解绑广告主",
)
async def post_unbind_advertisers(
    session: SessionDep,
    _principal: Menu63,
    body: UnbindAdvertisersBody,
) -> dict[str, Any]:
    """有执行中广告则整批拒绝。解绑是软删，同步不会把这户加回列表。"""
    await commands.unbind_advertisers(session, body.advertiser_ids)
    return success(None)


@router.post(
    "/advertisers/import",
    response_model=Envelope[ImportAdvertisersData],
    summary="导入分配或解绑广告主",
)
async def post_import_advertisers(
    session: SessionDep,
    principal: Menu63,
    action: Annotated[Literal["assign", "unbind"], Form()],
    file: Annotated[UploadFile, File()],
) -> dict[str, Any]:
    """按 xlsx 整份分配或解绑。表头与单批接口的拒绝规则相同。"""
    raw = await file.read()
    data = await commands.import_advertisers(session, action, raw, _operator(principal))
    return success(data)


@router.post(
    "/sync/advertisers",
    response_model=Envelope[SyncAdvertisersData],
    summary="手动同步广告主",
)
async def post_sync_advertisers(
    session: SessionDep,
    _principal: Menu64,
    query: Annotated[SyncAdvertisersQuery, Query()],
) -> dict[str, Any]:
    """拉名单、余额和公司名。mock 时不打开放平台。"""
    return success(await commands.sync_advertisers(session, query.oe_app_id))


@router.get(
    "/subjects",
    response_model=Envelope[PageData[SubjectItem]],
    summary="分页查询投放主体",
)
async def get_subjects(
    session: SessionDep,
    _principal: Menu65,
    query: Annotated[SubjectQuery, Query()],
) -> dict[str, Any]:
    """按名称、主体 id、投放模式和剧场类型筛选。"""
    return success(await commands.list_subjects(session, query))


@router.post(
    "/subjects",
    response_model=Envelope[SubjectItem],
    summary="创建投放主体",
)
async def post_subject(
    session: SessionDep,
    _principal: Menu65,
    body: SubjectBody,
) -> dict[str, Any]:
    """剧场三个字段都是文本。不提供删除。"""
    return success(await commands.create_subject(session, body))


@router.put(
    "/subjects/{subject_id}",
    response_model=Envelope[SubjectItem],
    summary="修改投放主体",
)
async def put_subject(
    subject_id: int,
    session: SessionDep,
    _principal: Menu65,
    body: SubjectBody,
) -> dict[str, Any]:
    """字段与创建相同。"""
    return success(await commands.update_subject(session, subject_id, body))


@router.get(
    "/douyin",
    response_model=Envelope[PageData[DouyinItem]],
    summary="分页查询抖音号",
)
async def get_douyin(
    session: SessionDep,
    _principal: Menu66,
    query: Annotated[DouyinQuery, Query()],
) -> dict[str, Any]:
    """全域和标准分两次查，delivery_mode 必填。"""
    return success(await commands.list_douyin(session, query))


@router.post(
    "/douyin",
    response_model=Envelope[DouyinItem],
    summary="创建抖音号",
)
async def post_douyin(
    session: SessionDep,
    principal: Menu66,
    body: DouyinBody,
) -> dict[str, Any]:
    """标准号拒绝部门和负责人。投手走分配接口。"""
    return success(await commands.create_douyin(session, body, _operator(principal)))


@router.put(
    "/douyin/{account_id}",
    response_model=Envelope[DouyinItem],
    summary="修改抖音号",
)
async def put_douyin(
    account_id: int,
    session: SessionDep,
    _principal: Menu66,
    body: DouyinUpdateBody,
) -> dict[str, Any]:
    """不改投手分配。从开到关时查占用。"""
    return success(await commands.update_douyin(session, account_id, body))


@router.post(
    "/douyin/{account_id}/enabled",
    response_model=Envelope[DouyinEnabledData],
    summary="抖音号启停",
)
async def post_douyin_enabled(
    account_id: int,
    session: SessionDep,
    _principal: Menu66,
    body: DouyinEnabledBody,
) -> dict[str, Any]:
    """从开到关之前查执行中广告。"""
    return success(await commands.set_douyin_enabled(session, account_id, body.enabled))


@router.post(
    "/douyin/{account_id}/assign",
    response_model=Envelope[DouyinAssignData],
    summary="分配全域抖音号投手",
)
async def post_douyin_assign(
    account_id: int,
    session: SessionDep,
    _principal: Menu66or67,
    body: AssignPitchersBody,
) -> dict[str, Any]:
    """覆盖该全域号的投手。标准号拒绝。"""
    return success(await commands.assign_douyin(session, account_id, body))


@router.post(
    "/douyin/{account_id}/reclaim",
    response_model=Envelope[DouyinReclaimData],
    summary="回收抖音号部门与负责人",
)
async def post_douyin_reclaim(
    account_id: int,
    session: SessionDep,
    _principal: Menu66,
) -> dict[str, Any]:
    """只清部门和负责人，投手分配保留。"""
    return success(await commands.reclaim_douyin(session, account_id))


@router.delete(
    "/douyin/{account_id}",
    response_model=Envelope[None],
    summary="软删抖音号",
)
async def delete_douyin(
    account_id: int,
    session: SessionDep,
    _principal: Menu66,
) -> dict[str, Any]:
    """有执行中广告则不删。"""
    await commands.delete_douyin(session, account_id)
    return success(None)


@router.get(
    "/product-libraries",
    response_model=Envelope[PageData[ProductLibraryItem]],
    summary="分页查询商品库",
)
async def get_product_libraries(
    session: SessionDep,
    _principal: Menu68,
    query: Annotated[ProductLibraryQuery, Query()],
) -> dict[str, Any]:
    """按名称、类型和组织筛选。"""
    return success(await commands.list_product_libraries(session, query))


@router.post(
    "/product-libraries",
    response_model=Envelope[ProductLibraryItem],
    summary="创建商品库",
)
async def post_product_library(
    session: SessionDep,
    _principal: Menu68,
    body: ProductLibraryBody,
) -> dict[str, Any]:
    """必填 library_role。不接收投手。"""
    return success(await commands.create_product_library(session, body))


@router.put(
    "/product-libraries/{library_id}",
    response_model=Envelope[ProductLibraryItem],
    summary="修改商品库",
)
async def put_product_library(
    library_id: int,
    session: SessionDep,
    _principal: Menu68,
    body: ProductLibraryBody,
) -> dict[str, Any]:
    """不改投手集合。第二个同组织同类型兜底库拒绝。"""
    return success(await commands.update_product_library(session, library_id, body))


@router.delete(
    "/product-libraries/{library_id}",
    response_model=Envelope[None],
    summary="软删商品库",
)
async def delete_product_library(
    library_id: int,
    session: SessionDep,
    _principal: Menu68,
) -> dict[str, Any]:
    """已有投手或已上传短剧时拒绝。"""
    await commands.delete_product_library(session, library_id)
    return success(None)


@router.post(
    "/product-libraries/{library_id}/assign-pitchers",
    response_model=Envelope[ProductLibraryAssignData],
    summary="覆盖商品库投手",
)
async def post_assign_library_pitchers(
    library_id: int,
    session: SessionDep,
    _principal: Menu68,
    body: AssignPitchersBody,
) -> dict[str, Any]:
    """只接受标准库。名单里有人已挂在同组织同类型的别的库则整批拒绝。"""
    return success(await commands.assign_product_library_pitchers(session, library_id, body))
