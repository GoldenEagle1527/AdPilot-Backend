"""账户管理与巨量夹具落库表。

公共列在 BaseModel：id、is_deleted、deleted_at、created_date、updated_date。
巨量侧 id 用 BigInteger，主键仍是库内 Integer Identity。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    desc,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import BaseModel

_TS = DateTime(timezone=True)

# 由迁移创建。mock 发号不靠进程全局变量。
OE_PROJECT_ID_SEQ = "oe_project_ocean_project_id_seq"
OE_VIDEO_ID_SEQ = "oe_video_ocean_video_id_seq"
OE_PRODUCT_ID_SEQ = "oe_product_ocean_product_id_seq"


class OeApp(BaseModel):
    """巨量应用。同一 channel 可以有多行。secret 只存配置键名。"""

    __tablename__ = "oe_app"
    __table_args__ = (
        CheckConstraint("channel IN ('self', 'third')", name="ck_oe_app_channel"),
        CheckConstraint("status IN ('active', 'disabled')", name="ck_oe_app_status"),
        UniqueConstraint("app_id", name="uq_oe_app_app_id"),
        {"comment": "巨量应用（自研或三方）。页面不能新增，只能改状态和备注。"},
    )

    channel: Mapped[str] = mapped_column(String(16), nullable=False, comment="self 自研、third 三方")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="展示名，区分自研/三方")
    app_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="巨量应用 id")
    secret: Mapped[str] = mapped_column(String(128), nullable=False, comment="配置键名，不存明文密钥")
    agent_key: Mapped[str] = mapped_column(String(64), nullable=False, comment="授权 state 的 agentId")
    agency: Mapped[bool] = mapped_column(Boolean, nullable=False, comment="自研授权链接带 agency=true")
    material_auth: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"), comment="素材授权，固定 1"
    )
    oauth_rid: Mapped[str] = mapped_column(String(64), nullable=False, comment="授权链接 rid")
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'active'"), comment="active 有效、disabled 停用"
    )
    remark: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="备注")


class OeToken(BaseModel):
    """每套应用当前一行令牌。换票成功后覆盖这一行。"""

    __tablename__ = "oe_token"
    __table_args__ = (
        UniqueConstraint("oe_app_id", name="uq_oe_token_oe_app_id"),
        Index("ix_oe_token_access_expire_at", "access_expire_at"),
        {"comment": "巨量应用当前令牌。access/refresh 存密文。"},
    )

    oe_app_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("oe_app.id", ondelete="CASCADE"), nullable=False, comment="所属应用"
    )
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True, comment="access_token 密文")
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True, comment="refresh_token 密文")
    access_expire_at: Mapped[datetime | None] = mapped_column(_TS, nullable=True, comment="access 过期时间")
    refresh_expire_at: Mapped[datetime | None] = mapped_column(_TS, nullable=True, comment="refresh 过期时间")
    last_refresh_at: Mapped[datetime | None] = mapped_column(_TS, nullable=True, comment="上次刷新成功时间")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="上次刷新失败摘要")


class OeOrganization(BaseModel):
    """授权组织。未删除的巨量账户 id 全局唯一。哪套应用授过权见 oe_organization_grant。"""

    __tablename__ = "oe_organization"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'invalid')", name="ck_oe_organization_status"),
        Index(
            "uq_oe_organization_ocean_account_alive",
            "ocean_account_id",
            unique=True,
            postgresql_where=text("is_deleted = 0"),
        ),
        Index("ix_oe_organization_status_alive", "status", postgresql_where=text("is_deleted = 0")),
        {"comment": "巨量授权组织。同一 ocean_account_id 只一行。status：active 有效、invalid 全部授权失效。"},
    )

    ocean_account_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="巨量账户 id")
    name: Mapped[str] = mapped_column(String(256), nullable=False, comment="组织名称")
    account_role: Mapped[str] = mapped_column(String(64), nullable=False, comment="巨量账户角色，原样保存")
    ocean_version: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="由 account_role 推出：升级版组织或旧版工作台"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'active'"), comment="active 有效、invalid 失效"
    )
    raw_payload: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="最近一次巨量原文，列表不返回"
    )
    ebp_account_task_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="超过 1 万条时的全量导出任务 id"
    )
    ebp_account_task_status: Mapped[str | None] = mapped_column(
        String(16), nullable=True, comment="导出任务状态：EXECUTING、COMPLETED、FAILED、EXPIRED"
    )


class OeOrganizationGrant(BaseModel):
    """一套应用对一个组织的授权。列表按这一行区分自研和三方。"""

    __tablename__ = "oe_organization_grant"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'invalid')", name="ck_oe_organization_grant_status"),
        Index(
            "uq_oe_organization_grant_alive",
            "organization_id",
            "oe_app_id",
            unique=True,
            postgresql_where=text("is_deleted = 0"),
        ),
        Index(
            "ix_oe_organization_grant_app_alive",
            "oe_app_id",
            postgresql_where=text("is_deleted = 0"),
        ),
        {"comment": "组织与应用的授权关系。失效只打在这一行，不连带另一套应用。"},
    )

    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("oe_organization.id", ondelete="RESTRICT"), nullable=False, comment="授权组织"
    )
    oe_app_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("oe_app.id", ondelete="RESTRICT"), nullable=False, comment="授权应用"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'active'"), comment="active 有效、invalid 这套应用已失效"
    )


class AdvertiserAccount(BaseModel):
    """广告主。一个户同时只属于一个投手；投手可拥有多个户。"""

    __tablename__ = "advertiser_account"
    __table_args__ = (
        CheckConstraint("sync_status IN ('active', 'missing')", name="ck_advertiser_account_sync_status"),
        Index(
            "uq_advertiser_account_advertiser_id_alive",
            "advertiser_id",
            unique=True,
            postgresql_where=text("is_deleted = 0"),
        ),
        Index(
            "ix_advertiser_account_organization_alive",
            "organization_id",
            postgresql_where=text("is_deleted = 0"),
        ),
        Index(
            "ix_advertiser_account_pitcher_alive",
            "pitcher_user_id",
            postgresql_where=text("is_deleted = 0 AND pitcher_user_id IS NOT NULL"),
        ),
        Index(
            "ix_advertiser_account_sync_status_alive",
            "sync_status",
            postgresql_where=text("is_deleted = 0"),
        ),
        Index(
            "ix_advertiser_account_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index(
            "ix_advertiser_account_local_name_trgm",
            "local_name",
            postgresql_using="gin",
            postgresql_ops={"local_name": "gin_trgm_ops"},
        ),
        {"comment": "广告主。解绑是软删，分配关系留在行上。"},
    )

    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("oe_organization.id", ondelete="RESTRICT"), nullable=False, comment="所属组织"
    )
    oe_app_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("oe_app.id", ondelete="RESTRICT"), nullable=False, comment="查余额和主体所用应用"
    )
    advertiser_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="巨量广告主 id")
    name: Mapped[str] = mapped_column(String(512), nullable=False, comment="巨量账户名")
    local_name: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="中台展示名，空则用 name"
    )
    valid_balance: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2), nullable=True, comment="可用余额，单位元"
    )
    raw_payload: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="最近一次巨量原文，列表不返回"
    )
    balance_synced_at: Mapped[datetime | None] = mapped_column(_TS, nullable=True, comment="余额同步时间")
    company_name: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="巨量公开信息中的公司名，不是投放主体"
    )
    company_synced_at: Mapped[datetime | None] = mapped_column(_TS, nullable=True, comment="公司名同步时间")
    pitcher_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, comment="投手，未分配为空"
    )
    assigned_at: Mapped[datetime | None] = mapped_column(_TS, nullable=True, comment="分配时间")
    assigned_by: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="分配人登录账号")
    sync_status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'active'"), comment="active 有效、missing 失效"
    )
    unbound_at: Mapped[datetime | None] = mapped_column(_TS, nullable=True, comment="解绑时间")


class AdvertiserNameLog(BaseModel):
    """广告主改名审计。批量改名每个户一行。时间用 created_date。"""

    __tablename__ = "advertiser_name_log"
    __table_args__ = (
        Index(
            "ix_advertiser_name_log_account_created",
            "advertiser_account_id",
            desc("created_date"),
        ),
        {"comment": "广告主改名审计"},
    )

    advertiser_account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("advertiser_account.id", ondelete="RESTRICT"),
        nullable=False,
        comment="广告主行",
    )
    old_name: Mapped[str] = mapped_column(String(512), nullable=False, comment="旧名")
    new_name: Mapped[str] = mapped_column(String(512), nullable=False, comment="新名")
    operator_account: Mapped[str] = mapped_column(String(64), nullable=False, comment="操作人登录账号")


class DeliverySubject(BaseModel):
    """投放主体。剧场只存文本，不建剧场外键。"""

    __tablename__ = "delivery_subject"
    __table_args__ = (
        CheckConstraint("delivery_mode IN ('standard', 'uni')", name="ck_delivery_subject_delivery_mode"),
        CheckConstraint("min_bid <= max_bid", name="ck_delivery_subject_bid_range"),
        Index(
            "uq_delivery_subject_subject_no_alive",
            "subject_no",
            unique=True,
            postgresql_where=text("is_deleted = 0"),
        ),
        Index(
            "ix_delivery_subject_mode_theater_alive",
            "delivery_mode",
            "theater_kind",
            postgresql_where=text("is_deleted = 0"),
        ),
        Index(
            "ix_delivery_subject_department_alive",
            "department_id",
            postgresql_where=text("is_deleted = 0"),
        ),
        Index("ix_delivery_subject_material_account", "material_account_id"),
        Index(
            "ix_delivery_subject_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        {"comment": "投放主体。人工录入。actual_bid、arpu 预留，接口不读写。"},
    )

    name: Mapped[str] = mapped_column(String(256), nullable=False, comment="主体名称")
    subject_no: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="主体 id")
    short_name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="简称")
    delivery_mode: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="standard 标准投放、uni 全域投放"
    )
    theater_name: Mapped[str] = mapped_column(String(256), nullable=False, comment="剧场名称")
    theater_kind: Mapped[str] = mapped_column(String(64), nullable=False, comment="剧场类型，如端原生")
    charge_mode: Mapped[str] = mapped_column(String(16), nullable=False, comment="收费模式，IAA 或 IAP")
    min_bid: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, comment="出价下限")
    max_bid: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, comment="出价上限")
    roi_goal: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True, comment="ROI，最多 3 位小数")
    department_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("departments.id", ondelete="RESTRICT"),
        nullable=True,
        comment="可用部门，空表示各部门都能用",
    )
    material_account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("advertiser_account.id", ondelete="RESTRICT"),
        nullable=False,
        comment="素材账户，须为未解绑广告主",
    )
    dual_bid: Mapped[bool] = mapped_column(
        Boolean, nullable=False, comment="真为出价加 ROI，假为只出价"
    )
    bid_panel: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="出价面板")
    actual_bid: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2), nullable=True, comment="实际出价，预留可空"
    )
    arpu: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True, comment="ARPU，预留可空")


class DouyinAccount(BaseModel):
    """抖音号。标准号不填部门和负责人，由检查约束卡住。"""

    __tablename__ = "douyin_account"
    __table_args__ = (
        CheckConstraint("delivery_mode IN ('uni', 'standard')", name="ck_douyin_account_delivery_mode"),
        CheckConstraint(
            "delivery_mode <> 'standard' OR (department_id IS NULL AND owner_user_id IS NULL)",
            name="ck_douyin_account_standard_no_owner",
        ),
        Index(
            "uq_douyin_account_mode_aweme_alive",
            "delivery_mode",
            "aweme_id",
            unique=True,
            postgresql_where=text("is_deleted = 0"),
        ),
        Index(
            "ix_douyin_account_mode_department_alive",
            "delivery_mode",
            "department_id",
            postgresql_where=text("is_deleted = 0"),
        ),
        Index(
            "ix_douyin_account_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        {"comment": "抖音号。department_id 与 owner_user_id 仅全域使用。"},
    )

    aweme_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="抖音号")
    name: Mapped[str] = mapped_column(String(256), nullable=False, comment="名称")
    delivery_mode: Mapped[str] = mapped_column(String(16), nullable=False, comment="uni 全域、standard 标准")
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true"), comment="是否启用"
    )
    department_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=True, comment="归属部门，仅全域"
    )
    owner_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, comment="部门负责人，仅全域"
    )
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="创建人登录账号")


class DouyinPitcher(BaseModel):
    """全域抖音号与投手。标准号禁止插入，由应用层保证。"""

    __tablename__ = "douyin_pitcher"
    __table_args__ = (
        UniqueConstraint("douyin_account_id", "user_id", name="uq_douyin_pitcher_account_user"),
        Index("ix_douyin_pitcher_user_id", "user_id"),
        {"comment": "全域抖音号分配的投手。标准号禁止插入，应用层保证。"},
    )

    douyin_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("douyin_account.id", ondelete="CASCADE"), nullable=False, comment="抖音号"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="投手"
    )


class ProductLibrary(BaseModel):
    """商品库。建库不写投手。同一组织同一类型最多一个兜底库。"""

    __tablename__ = "product_library"
    __table_args__ = (
        CheckConstraint("library_kind IN ('novel', 'video')", name="ck_product_library_kind"),
        CheckConstraint("library_role IN ('fallback', 'standard')", name="ck_product_library_role"),
        CheckConstraint("uploaded_count >= 0", name="ck_product_library_uploaded_count"),
        Index(
            "uq_product_library_library_no_alive",
            "library_no",
            unique=True,
            postgresql_where=text("is_deleted = 0"),
        ),
        Index(
            "uq_product_library_fallback_alive",
            "organization_id",
            "library_kind",
            unique=True,
            postgresql_where=text("library_role = 'fallback' AND is_deleted = 0"),
        ),
        Index(
            "ix_product_library_org_kind_role_alive",
            "organization_id",
            "library_kind",
            "library_role",
            postgresql_where=text("is_deleted = 0"),
        ),
        {"comment": "商品库。没有投手列，投手在 product_library_pitcher。"},
    )

    name: Mapped[str] = mapped_column(String(256), nullable=False, comment="库名称")
    library_no: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="巨量商品库 id")
    library_kind: Mapped[str] = mapped_column(String(16), nullable=False, comment="novel 小说库、video 视频库")
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("oe_organization.id", ondelete="RESTRICT"), nullable=False, comment="所属组织"
    )
    library_role: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="fallback 兜底、standard 标准"
    )
    uploaded_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"), comment="已上传短剧数"
    )


class ProductLibraryPitcher(BaseModel):
    """标准库与投手。同一组织、同一类型下一个投手只挂一个库。"""

    __tablename__ = "product_library_pitcher"
    __table_args__ = (
        CheckConstraint(
            "library_kind IN ('novel', 'video')", name="ck_product_library_pitcher_kind"
        ),
        UniqueConstraint(
            "user_id",
            "organization_id",
            "library_kind",
            name="uq_product_library_pitcher_user_org_kind",
        ),
        Index("ix_product_library_pitcher_library", "product_library_id"),
        {
            "comment": "标准库投手。只允许挂 standard 库，由应用层保证；兜底库不允许插入。"
        },
    )

    product_library_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("product_library.id", ondelete="CASCADE"), nullable=False, comment="商品库"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="投手"
    )
    organization_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("oe_organization.id", ondelete="RESTRICT"),
        nullable=False,
        comment="从库抄下的组织，用于唯一约束",
    )
    library_kind: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="从库抄下的类型，novel 或 video"
    )


class AccountSyncRun(BaseModel):
    """一次同步一条。同一应用同一类型未结束时只能有一行。"""

    __tablename__ = "account_sync_run"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('org', 'advertiser', 'balance', 'company', 'token_refresh', 'report')",
            name="ck_account_sync_run_kind",
        ),
        CheckConstraint("success_count >= 0 AND failure_count >= 0", name="ck_account_sync_run_counts"),
        Index(
            "uq_account_sync_run_open",
            "oe_app_id",
            "kind",
            unique=True,
            postgresql_where=text("finished_at IS NULL"),
        ),
        Index(
            "ix_account_sync_run_app_kind_started",
            "oe_app_id",
            "kind",
            desc("started_at"),
        ),
        {"comment": "同步排障记录。管理页不展示。"},
    )

    oe_app_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("oe_app.id", ondelete="RESTRICT"), nullable=False, comment="所属应用"
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False, comment="同步类型")
    started_at: Mapped[datetime] = mapped_column(
        _TS, nullable=False, server_default=text("now()"), comment="开始时间"
    )
    finished_at: Mapped[datetime | None] = mapped_column(_TS, nullable=True, comment="结束时间，空表示进行中")
    success_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"), comment="成功数"
    )
    failure_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"), comment="失败数"
    )
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误摘要")


class OeProject(BaseModel):
    """巨量项目，替换内存 PROJECTS。"""

    __tablename__ = "oe_project"
    __table_args__ = (
        UniqueConstraint("ocean_project_id", name="uq_oe_project_ocean_project_id"),
        Index(
            "ix_oe_project_advertiser_created_alive",
            "advertiser_id",
            desc("created_date"),
            postgresql_where=text("is_deleted = 0"),
        ),
        {"comment": "巨量项目。template 列表不选出。ocean_project_id 由序列从 7000000000000001 起发。"},
    )

    advertiser_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="巨量广告主 id")
    ocean_project_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text(f"nextval('{OE_PROJECT_ID_SEQ}')"),
        comment="巨量项目 id",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="项目名称")
    landing_type: Mapped[str] = mapped_column(String(64), nullable=False, server_default=text("''"), comment="推广目的")
    marketing_goal: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default=text("''"), comment="营销场景"
    )
    ad_type: Mapped[str] = mapped_column(String(64), nullable=False, server_default=text("''"), comment="广告类型")
    delivery_mode: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default=text("''"), comment="投放模式"
    )
    subject_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("delivery_subject.id", ondelete="RESTRICT"), nullable=True, comment="投放主体"
    )
    template: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="模板，列表不选出")
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="最近一次巨量原文，列表不返回")


class OeVideo(BaseModel):
    """巨量视频。ocean_video_id 保存开放平台返回的字符串。"""

    __tablename__ = "oe_video"
    __table_args__ = (
        UniqueConstraint("ocean_video_id", name="uq_oe_video_ocean_video_id"),
        Index(
            "ix_oe_video_advertiser_created_alive",
            "advertiser_id",
            desc("created_date"),
            postgresql_where=text("is_deleted = 0"),
        ),
        {"comment": "巨量视频。ocean_video_id 是开放平台 video_id。"},
    )

    advertiser_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="巨量广告主 id")
    video_url: Mapped[str] = mapped_column(String(2048), nullable=False, comment="视频地址")
    ocean_video_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="巨量视频 id，开放平台返回的字符串"
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("''"), comment="状态")
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="最近一次巨量原文，列表不返回")


class OeProduct(BaseModel):
    """巨量商品，替换内存 PRODUCTS。上传成功时同一事务增加商品库计数。"""

    __tablename__ = "oe_product"
    __table_args__ = (
        Index(
            "ix_oe_product_library_alive",
            "product_library_id",
            postgresql_where=text("is_deleted = 0"),
        ),
        {"comment": "巨量商品。ocean_product_id 由序列从 9001 起发。"},
    )

    product_library_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("product_library.id", ondelete="RESTRICT"), nullable=False, comment="商品库"
    )
    drama_name: Mapped[str] = mapped_column(String(512), nullable=False, comment="短剧名")
    file_url: Mapped[str] = mapped_column(String(2048), nullable=False, comment="文件地址")
    ocean_product_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text(f"nextval('{OE_PRODUCT_ID_SEQ}')"),
        comment="巨量商品 id",
    )
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="最近一次巨量原文，列表不返回")


class OePromotion(BaseModel):
    """广告启停状态，替换内存 PROMOTIONS。占用检查看 ENABLE 且未删除。"""

    __tablename__ = "oe_promotion"
    __table_args__ = (
        CheckConstraint("opt_status IN ('ENABLE', 'DISABLE')", name="ck_oe_promotion_opt_status"),
        UniqueConstraint("advertiser_id", "promotion_id", name="uq_oe_promotion_advertiser_promotion"),
        Index(
            "ix_oe_promotion_advertiser_enable",
            "advertiser_id",
            postgresql_where=text("opt_status = 'ENABLE' AND is_deleted = 0"),
        ),
        Index(
            "ix_oe_promotion_douyin_enable",
            "douyin_account_id",
            postgresql_where=text(
                "opt_status = 'ENABLE' AND is_deleted = 0 AND douyin_account_id IS NOT NULL"
            ),
        ),
        {"comment": "广告状态。解绑和回收走 ENABLE 部分索引。"},
    )

    advertiser_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="巨量广告主 id")
    promotion_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="巨量广告 id")
    opt_status: Mapped[str] = mapped_column(String(16), nullable=False, comment="ENABLE 或 DISABLE")
    name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="广告名，占用提示用")
    douyin_account_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("douyin_account.id", ondelete="RESTRICT"),
        nullable=True,
        comment="占用该抖音号的广告，现有启停可不填",
    )
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="启停回包原文，列表不返回")


class OeReportSnapshot(BaseModel):
    """当前报表快照。一行一个广告，同步时 upsert，不追加历史。"""

    __tablename__ = "oe_report_snapshot"
    __table_args__ = (
        UniqueConstraint("advertiser_id", "promotion_id", name="uq_oe_report_snapshot_advertiser_promotion"),
        Index("ix_oe_report_snapshot_advertiser_id", "advertiser_id"),
        {"comment": "报表当前快照。不建历史表。"},
    )

    advertiser_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="巨量广告主 id")
    promotion_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="巨量广告 id")
    stat_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, comment="消耗")
    attribution_micro_game_0d_roi: Mapped[Decimal] = mapped_column(
        Numeric(10, 3), nullable=False, comment="小游戏当日 ROI"
    )
    synced_at: Mapped[datetime] = mapped_column(_TS, nullable=False, comment="快照时间")
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="最近一次巨量原文，列表不返回")
