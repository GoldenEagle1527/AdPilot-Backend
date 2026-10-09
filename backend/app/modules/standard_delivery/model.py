"""漫剧标准投放的本地草稿：模板、任务草稿、自动规则。

只存本系统要留的字段。不调用创建项目、创建单元，也不写巨量提交体。
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import BaseModel

_TS = DateTime(timezone=True)


class ChargeMode(StrEnum):
    """免费 IAA、付费 IAP。和投放主体的收费模式用同一套值。"""

    IAA = "IAA"
    IAP = "IAP"


class TemplateMode(StrEnum):
    """模板属于标准投放还是全域投放。列名用 delivery_mode，和主体、抖音号一致。"""

    STANDARD = "standard"
    UNI = "uni"


class TitleSelectMode(StrEnum):
    """标题选择。手动从标题库挑，或按类型自动给。

    全域写在 title_select_mode。标准写在 standard_title_select_mode，两列不混用。
    """

    MANUAL = "manual"
    AUTO = "auto"


class AudienceDistrict(StrEnum):
    """用户定向里的地域。不限，或按行政区域选城市。"""

    NONE = "NONE"
    REGION = "REGION"


class AudienceGender(StrEnum):
    """用户定向里的性别。不限、男、女。"""

    NONE = "none"
    MALE = "male"
    FEMALE = "female"


class AgeBand(StrEnum):
    """用户定向里的年龄段。空列表表示不限，不另存一个不限标记。"""

    B18_23 = "18_23"
    B24_30 = "24_30"
    B31_40 = "31_40"
    B41_49 = "41_49"
    B50_PLUS = "50_plus"


class ProductSelect(StrEnum):
    """商品选择。本剧、非本剧，或手动选择。"""

    THIS_SERIES = "this_series"
    OTHER_SERIES = "other_series"
    MANUAL = "manual"


class LibraryKind(StrEnum):
    """商品库类型。模板只记视频库或小说库，不记某一行商品库。"""

    VIDEO = "video"
    NOVEL = "novel"


class OceanDeliveryMode(StrEnum):
    """巨量创建项目的投放模式。不是本表的 delivery_mode。"""

    MANUAL = "MANUAL"
    PROCEDURAL = "PROCEDURAL"


class BidType(StrEnum):
    """竞价策略。稳定成本或最大转化。"""

    CUSTOM = "CUSTOM"
    NO_BID = "NO_BID"


class ScheduleType(StrEnum):
    """投放时间。从今天起，或自选起止日期。"""

    FROM_NOW = "SCHEDULE_FROM_NOW"
    START_END = "SCHEDULE_START_END"


class OperationStatus(StrEnum):
    """项目或广告的开关。"""

    ENABLE = "ENABLE"
    DISABLE = "DISABLE"


# 旧标准行可以整组留空。新标准行把巨量字段写满。全域行这组必须为空。
_STANDARD_LEGACY = (
    "ocean_delivery_mode IS NULL "
    "AND bid_type IS NULL "
    "AND schedule_type IS NULL "
    "AND schedule_start_date IS NULL "
    "AND schedule_end_date IS NULL "
    "AND schedule_time IS NULL "
    "AND ad_source IS NULL "
    "AND product_name IS NULL "
    "AND cardinality(selling_points) = 0 "
    "AND cardinality(call_to_action_buttons) = 0 "
    "AND roi_goal IS NULL "
    "AND videos_per_ad IS NULL "
    "AND titles_per_ad IS NULL"
)
_STANDARD_FILLED = (
    "ocean_delivery_mode IN ('MANUAL', 'PROCEDURAL') "
    "AND bid_type IN ('CUSTOM', 'NO_BID') "
    "AND ("
    "(schedule_type = 'SCHEDULE_FROM_NOW' AND schedule_start_date IS NULL AND schedule_end_date IS NULL) "
    "OR (schedule_type = 'SCHEDULE_START_END' AND schedule_start_date IS NOT NULL "
    "AND schedule_end_date IS NOT NULL AND schedule_start_date <= schedule_end_date)"
    ") "
    "AND (schedule_time IS NULL OR (char_length(schedule_time) = 336 AND schedule_time ~ '^[01]*$')) "
    "AND char_length(ad_source) BETWEEN 1 AND 100 "
    "AND char_length(product_name) BETWEEN 1 AND 20 "
    "AND cardinality(selling_points) <= 10 "
    "AND cardinality(call_to_action_buttons) <= 10 "
    "AND (roi_goal IS NULL OR (roi_goal >= 0 AND roi_goal <= 9999.999)) "
    "AND videos_per_ad BETWEEN 1 AND 30 "
    "AND titles_per_ad BETWEEN 1 AND 10"
)

# 标准行可以写项目预算和下面这些列。全域专用的 ROI 系数、AIGC、标题列仍必须为空。
_STANDARD_EXTRAS = (
    "(placement IS NULL OR placement IN ('aweme', 'aweme_feed', 'universal')) "
    "AND (district IS NULL OR district IN ('NONE', 'REGION')) "
    "AND (district IS DISTINCT FROM 'NONE' OR city_codes IS NULL OR cardinality(city_codes) = 0) "
    "AND (district IS DISTINCT FROM 'REGION' OR (city_codes IS NOT NULL AND cardinality(city_codes) > 0)) "
    "AND (project_budget IS NULL OR (project_budget > 0 AND project_budget <= 99999999.99)) "
    "AND (ad_budget IS NULL OR (ad_budget > 0 AND ad_budget <= 99999999.99)) "
    "AND (library_kind IS NULL OR library_kind IN ('video', 'novel')) "
    "AND (product_select IS NULL OR product_select IN ('this_series', 'other_series', 'manual')) "
    "AND (promotion_operation IS NULL OR promotion_operation IN ('ENABLE', 'DISABLE')) "
    "AND (product_image_id IS NULL OR (product_image_id LIKE 'img-%' AND char_length(product_image_id) BETWEEN 5 AND 64)) "
    "AND (standard_title_select_mode IS NULL OR standard_title_select_mode IN ('manual', 'auto')) "
    "AND (gender IS NULL OR gender IN ('none', 'male', 'female')) "
    "AND (age_bands IS NULL OR (cardinality(age_bands) <= 5 "
    "AND age_bands <@ ARRAY['18_23', '24_30', '31_40', '41_49', '50_plus']::varchar[]))"
)
# 全域创建页要留下投放模式、排期和产品信息。标准专用的出价、条数和定向仍必须为空。
_UNI_PAGE = (
    "(ocean_delivery_mode IS NULL OR ocean_delivery_mode IN ('MANUAL', 'PROCEDURAL')) "
    "AND bid_type IS NULL "
    "AND ("
    "schedule_type IS NULL "
    "OR (schedule_type = 'SCHEDULE_FROM_NOW' AND schedule_start_date IS NULL AND schedule_end_date IS NULL) "
    "OR (schedule_type = 'SCHEDULE_START_END' AND schedule_start_date IS NOT NULL "
    "AND schedule_end_date IS NOT NULL AND schedule_start_date <= schedule_end_date)"
    ") "
    "AND (schedule_time IS NULL OR (char_length(schedule_time) = 336 AND schedule_time ~ '^[01]*$')) "
    "AND (ad_source IS NULL OR char_length(ad_source) BETWEEN 1 AND 100) "
    "AND (product_name IS NULL OR char_length(product_name) BETWEEN 1 AND 20) "
    "AND cardinality(selling_points) <= 10 "
    "AND cardinality(call_to_action_buttons) <= 10 "
    "AND roi_goal IS NULL "
    "AND videos_per_ad IS NULL "
    "AND titles_per_ad IS NULL "
    "AND ad_budget IS NULL"
)
# 全域行不写标准专用列。素材起量开关在全域上也留空。
_UNI_EXTRAS_EMPTY = (
    "placement IS NULL "
    "AND district IS NULL "
    "AND city_codes IS NULL "
    "AND product_library_id IS NULL "
    "AND library_kind IS NULL "
    "AND product_select IS NULL "
    "AND material_boost IS NULL "
    "AND promotion_operation IS NULL "
    "AND douyin_account_id IS NULL "
    "AND product_image_id IS NULL "
    "AND standard_title_select_mode IS NULL "
    "AND gender IS NULL "
    "AND age_bands IS NULL"
)
# 标准行不写全域专用列；全域行不写标准提交列，出价面板留空。
_TEMPLATE_SHAPE = (
    "("
    "delivery_mode = 'standard' "
    "AND roi_coefficient IS NULL "
    "AND aigc_dynamic_creative IS NULL "
    "AND title_select_mode IS NULL "
    "AND ads_per_account BETWEEN 1 AND 100 "
    f"AND {_STANDARD_EXTRAS} "
    f"AND (({_STANDARD_LEGACY}) OR ({_STANDARD_FILLED}))"
    ") OR ("
    "delivery_mode = 'uni' "
    "AND project_budget IS NOT NULL AND project_budget > 0 AND project_budget <= 99999999.99 "
    "AND roi_coefficient IS NOT NULL AND roi_coefficient >= 0 AND roi_coefficient <= 9999.999 "
    "AND aigc_dynamic_creative IS NOT NULL "
    "AND title_select_mode IN ('manual', 'auto') "
    "AND ads_per_account IS NULL "
    "AND cardinality(bid_panels) = 0 "
    f"AND ({_UNI_PAGE}) "
    f"AND {_UNI_EXTRAS_EMPTY}"
    ")"
)


class Placement(StrEnum):
    """版位。抖音必选；头条是在抖音上再加；通投智能选单独一种。"""

    AWEME = "aweme"
    AWEME_FEED = "aweme_feed"
    UNIVERSAL = "universal"


class OptimizeGoal(StrEnum):
    """优化目标。免费只允许激活，付费只允许付费。"""

    ACTIVE = "AD_CONVERT_TYPE_ACTIVE"
    PAY = "AD_CONVERT_TYPE_PAY"


GOAL_BY_CHARGE = {
    ChargeMode.IAA: OptimizeGoal.ACTIVE,
    ChargeMode.IAP: OptimizeGoal.PAY,
}


class DeliveryTemplate(BaseModel):
    """投放模板。标准与全域共用名称、主体、收费模式、时间和软删。

    标准行写出价面板、每账户广告条数、确认提交要用的巨量字段，以及版位、定向、性别、年龄、
    项目预算、商品策略、广告开关、一个标准抖音号、产品主图和标准标题选择。
    全域行写项目预算、ROI 系数、AIGC 和 title_select_mode。标准接口只读写 delivery_mode=standard。
    标准行的 ROI 用 roi_goal，不用 roi_coefficient。标准标题选择写 standard_title_select_mode。
    全域行上的标准提交列和标准专用列保持为空。
    """

    __tablename__ = "delivery_template"
    __table_args__ = (
        CheckConstraint("charge_mode IN ('IAA', 'IAP')", name="ck_delivery_template_charge"),
        CheckConstraint("delivery_mode IN ('standard', 'uni')", name="ck_delivery_template_delivery_mode"),
        CheckConstraint(_TEMPLATE_SHAPE, name="ck_delivery_template_mode_shape"),
        Index(
            "uq_delivery_template_mode_charge_name_alive",
            "delivery_mode",
            "charge_mode",
            "name",
            unique=True,
            postgresql_where=text("is_deleted = 0"),
        ),
        Index(
            "ix_delivery_template_charge_alive",
            "charge_mode",
            postgresql_where=text("is_deleted = 0"),
        ),
        Index(
            "ix_delivery_template_mode_charge_alive",
            "delivery_mode",
            "charge_mode",
            postgresql_where=text("is_deleted = 0"),
        ),
        {"comment": "投放模板。delivery_mode 区分标准与全域。标准专用列在全域行为空。不存 asset_ids。"},
    )

    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="模板名称")
    delivery_mode: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=TemplateMode.STANDARD,
        server_default=text("'standard'"),
        comment="standard 标准投放、uni 全域投放",
    )
    charge_mode: Mapped[str] = mapped_column(
        String(8), nullable=False, comment="投放变现模式：IAA 免费、IAP 付费"
    )
    subject_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("delivery_subject.id", ondelete="RESTRICT"),
        nullable=False,
        comment="投放主体。标准模板须为标准投放，全域模板须为全域投放，收费模式一致",
    )
    bid_panels: Mapped[list[str]] = mapped_column(
        ARRAY(String(64)),
        nullable=False,
        default=list,
        server_default=text("ARRAY[]::varchar[]"),
        comment="出价面板，从主体的 bid_panel 里多选。免费可空。全域模板为空数组",
    )
    ads_per_account: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="每账户广告条数，1–100。仅标准模板，全域为空"
    )
    ocean_delivery_mode: Mapped[str | None] = mapped_column(
        String(16), nullable=True, comment="巨量投放模式 MANUAL 或 PROCEDURAL。不是 delivery_mode。仅标准模板"
    )
    bid_type: Mapped[str | None] = mapped_column(
        String(16), nullable=True, comment="竞价策略 CUSTOM 或 NO_BID。仅标准模板"
    )
    schedule_type: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="投放时间 SCHEDULE_FROM_NOW 或 SCHEDULE_START_END。仅标准模板"
    )
    schedule_start_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="投放开始日期。仅 SCHEDULE_START_END，仅标准模板"
    )
    schedule_end_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="投放结束日期。仅 SCHEDULE_START_END，仅标准模板"
    )
    schedule_time: Mapped[str | None] = mapped_column(
        String(336), nullable=True, comment="投放时段。空表示不限。有值则为 48×7 的 0/1 串。仅标准模板"
    )
    ad_source: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="广告来源。仅标准模板"
    )
    product_name: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="产品名称，最多 20 字。仅标准模板"
    )
    selling_points: Mapped[list[str]] = mapped_column(
        ARRAY(String(20)),
        nullable=False,
        default=list,
        server_default=text("ARRAY[]::varchar[]"),
        comment="产品卖点。仅标准模板，全域为空数组",
    )
    call_to_action_buttons: Mapped[list[str]] = mapped_column(
        ARRAY(String(20)),
        nullable=False,
        default=list,
        server_default=text("ARRAY[]::varchar[]"),
        comment="行动号召。仅标准模板，全域为空数组",
    )
    roi_goal: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 3), nullable=True, comment="ROI 目标。仅标准模板。标准行不用 roi_coefficient"
    )
    videos_per_ad: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="每个广告使用视频数，1–30。仅标准模板"
    )
    titles_per_ad: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="每个广告使用标题数，1–10。仅标准模板"
    )
    project_budget: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, comment="项目预算，单位元。标准创建必填，类型为设置预算"
    )
    ad_budget: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, comment="广告预算，单位元。仅标准模板，不拿项目预算代替"
    )
    roi_coefficient: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 3), nullable=True, comment="ROI 系数。仅全域模板"
    )
    aigc_dynamic_creative: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, comment="AIGC 动态创意。仅全域模板"
    )
    title_select_mode: Mapped[str | None] = mapped_column(
        String(16), nullable=True, comment="标题选择：manual 手动、auto 自动。仅全域模板"
    )
    placement: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="版位：aweme 抖音、aweme_feed 抖音加头条、universal 通投智选。手动版位含抖音信息流。仅标准模板",
    )
    district: Mapped[str | None] = mapped_column(
        String(16), nullable=True, comment="用户定向地域：NONE 不限、REGION 行政区域。仅标准模板"
    )
    city_codes: Mapped[list[int] | None] = mapped_column(
        ARRAY(Integer), nullable=True, comment="行政区域城市编码。不限时为空。仅标准模板"
    )
    gender: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="用户定向性别：none 不限、male 男、female 女。空按不限。仅标准模板",
    )
    age_bands: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(16)),
        nullable=True,
        comment="用户定向年龄段。空表示不限。取值 18_23、24_30、31_40、41_49、50_plus。仅标准模板",
    )
    product_library_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("product_library.id", ondelete="RESTRICT"),
        nullable=True,
        comment="账户管理里绑定的一条视频库或小说库。仅标准模板",
    )
    library_kind: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="商品库类型：video 视频库、novel 小说库。不存具体商品库行。仅标准模板",
    )
    product_select: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="商品选择：this_series 本剧、other_series 非本剧、manual 手动选择。仅标准模板",
    )
    material_boost: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment="素材一键起量开关。产品说明没有这一项，标准模板默认关。仅标准模板",
    )
    promotion_operation: Mapped[str | None] = mapped_column(
        String(16), nullable=True, comment="广告开关 ENABLE 或 DISABLE。不是项目开关。仅标准模板"
    )
    douyin_account_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("douyin_account.id", ondelete="RESTRICT"),
        nullable=True,
        comment="一个标准抖音号。不使用全域按投手分配的表。仅标准模板",
    )
    product_image_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="产品主图 id，img- 前缀。仅标准模板"
    )
    standard_title_select_mode: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="标准模板标题选择 manual 或 auto。不是全域列 title_select_mode",
    )


class DeliveryTaskDraft(BaseModel):
    """投放任务草稿。一次只有一个抖音号，账户列表共用这一个号。

    album_url 保存要提交的推广链接：已有剧场链或手填，缺省时自动匹配 IAA。
    版位、项目预算、商品库、广告开关、抖音号可以留空，确认提交时改用模板上的值。
    不存事件资产、巨量商品 id、巨量视频 id。
    """

    __tablename__ = "delivery_task_draft"
    __table_args__ = (
        CheckConstraint("charge_mode IN ('IAA', 'IAP')", name="ck_delivery_task_draft_charge"),
        CheckConstraint(
            "placement IS NULL OR placement IN ('aweme', 'aweme_feed', 'universal')",
            name="ck_delivery_task_draft_placement",
        ),
        CheckConstraint(
            "(charge_mode = 'IAA' AND optimize_goal = 'AD_CONVERT_TYPE_ACTIVE') OR "
            "(charge_mode = 'IAP' AND optimize_goal = 'AD_CONVERT_TYPE_PAY')",
            name="ck_delivery_task_draft_goal",
        ),
        CheckConstraint(
            "(project_budget IS NULL OR project_budget > 0) AND ad_budget > 0",
            name="ck_delivery_task_draft_budget",
        ),
        CheckConstraint(
            "(schedule_start IS NULL AND schedule_end IS NULL) OR "
            "(schedule_start IS NOT NULL AND schedule_end IS NOT NULL AND schedule_start < schedule_end)",
            name="ck_delivery_task_draft_schedule",
        ),
        CheckConstraint(
            "project_operation IS NULL OR project_operation IN ('ENABLE', 'DISABLE')",
            name="ck_delivery_task_draft_project_operation",
        ),
        CheckConstraint(
            "promotion_operation IS NULL OR promotion_operation IN ('ENABLE', 'DISABLE')",
            name="ck_delivery_task_draft_promotion_operation",
        ),
        Index(
            "ix_delivery_task_draft_pitcher_charge",
            "pitcher_user_id",
            "charge_mode",
            postgresql_where=text("is_deleted = 0"),
        ),
        {"comment": "漫剧标准投放任务草稿。只给当前投手看自己的。确认提交不在本表。不存地域和 asset_ids。"},
    )

    template_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("delivery_template.id", ondelete="RESTRICT"),
        nullable=False,
        comment="投放模板",
    )
    charge_mode: Mapped[str] = mapped_column(
        String(8), nullable=False, comment="从模板抄来的收费模式，不随请求改"
    )
    pitcher_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="创建草稿的投手，列表只看自己的",
    )
    schedule_start: Mapped[datetime | None] = mapped_column(
        _TS, nullable=True, comment="预约执行开始。空表示未预约"
    )
    schedule_end: Mapped[datetime | None] = mapped_column(
        _TS, nullable=True, comment="预约执行结束。与开始同时空或同时有值"
    )
    douyin_account_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("douyin_account.id", ondelete="RESTRICT"),
        nullable=True,
        comment="唯一的标准抖音号。空则确认提交用模板上的号。多个账户共用，不按投手过滤",
    )
    series_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("manhua_series.id", ondelete="RESTRICT"),
        nullable=False,
        comment="一部短剧",
    )
    placement: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="版位：aweme 抖音、aweme_feed 抖音加头条、universal 通投智选。空则确认提交用模板",
    )
    project_budget: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, comment="项目预算，单位元。空则确认提交用模板"
    )
    ad_budget: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, comment="广告预算，单位元")
    optimize_goal: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="优化目标。免费激活，付费付费"
    )
    product_library_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("product_library.id", ondelete="RESTRICT"),
        nullable=True,
        comment="商品库。空则确认提交用模板上的商品库",
    )
    album_url: Mapped[str | None] = mapped_column(
        String(2048), nullable=True, comment="要提交的推广链接。已有剧场链、手填，或自动匹配的 IAA"
    )
    promotion_link_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="选中的剧场推广链。手填或自动匹配时为空"
    )
    link_name: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="推广链接名称，原生-加短剧前两字"
    )
    series_short_name: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="短剧简称，剧名前两个字"
    )
    product_book_name: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="非本剧时要上传的商品剧名"
    )
    video_order: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="upload",
        server_default=text("'upload'"),
        comment="视频顺序：upload 上传顺序、random 随机",
    )
    batch_titles: Mapped[list[str]] = mapped_column(
        ARRAY(String(55)),
        nullable=False,
        default=list,
        server_default=text("ARRAY[]::varchar[]"),
        comment="批量粘贴的临时标题，5–55 个字，不写入标题库",
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        _TS, nullable=True, comment="确认提交或预约到点提交的时间。空表示还没提交"
    )
    project_operation: Mapped[str | None] = mapped_column(
        String(16), nullable=True, comment="项目开关 ENABLE 或 DISABLE"
    )
    promotion_operation: Mapped[str | None] = mapped_column(
        String(16), nullable=True, comment="广告开关 ENABLE 或 DISABLE"
    )


class DeliveryTaskAccount(BaseModel):
    """草稿上的广告账户。整表替换，投手必须是这些户当前的投手。"""

    __tablename__ = "delivery_task_account"
    __table_args__ = (
        Index(
            "uq_delivery_task_account_pair",
            "task_id",
            "advertiser_account_id",
            unique=True,
        ),
        Index("ix_delivery_task_account_task", "task_id", "sort_order"),
        {"comment": "草稿账户。存的是广告主行，请求里用巨量广告主 id。"},
    )

    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("delivery_task_draft.id", ondelete="CASCADE"),
        nullable=False,
        comment="草稿",
    )
    advertiser_account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("advertiser_account.id", ondelete="RESTRICT"),
        nullable=False,
        comment="广告主行",
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="请求里的顺序，从 0 起")


class DeliveryTaskVideo(BaseModel):
    """草稿上的视频素材。须属于所选短剧，且当前用户能看见。"""

    __tablename__ = "delivery_task_video"
    __table_args__ = (
        Index("uq_delivery_task_video_pair", "task_id", "material_video_id", unique=True),
        Index("ix_delivery_task_video_task", "task_id", "sort_order"),
        {"comment": "草稿视频。只存素材库主键，不存巨量 video_id。"},
    )

    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("delivery_task_draft.id", ondelete="CASCADE"),
        nullable=False,
        comment="草稿",
    )
    # 素材表不在现有迁移链里，本地库也可能还没有。这里只存主键，保存时再查 material_videos。
    material_video_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="视频素材 material_videos.id，应用层校验"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="请求里的顺序，从 0 起")


class DeliveryTaskTitle(BaseModel):
    """草稿上的标题。只收当前用户自己上传的标题。"""

    __tablename__ = "delivery_task_title"
    __table_args__ = (
        Index("uq_delivery_task_title_pair", "task_id", "material_title_id", unique=True),
        Index("ix_delivery_task_title_task", "task_id", "sort_order"),
        {"comment": "草稿标题。只存标题库主键。"},
    )

    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("delivery_task_draft.id", ondelete="CASCADE"),
        nullable=False,
        comment="草稿",
    )
    # 标题表同样不在现有迁移链里。保存时再查 material_titles。
    material_title_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="标题 material_titles.id，应用层校验"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="请求里的顺序，从 0 起")


class DeliveryAutoRule(BaseModel):
    """自动投放规则。没有 schedule_start 时立即执行一次；有则到点执行一次。

    剧场固定为番茄漫剧。名称按规则类型生成。
    """

    __tablename__ = "delivery_auto_rule"
    __table_args__ = (
        CheckConstraint("charge_mode IN ('IAA', 'IAP')", name="ck_delivery_auto_rule_charge"),
        CheckConstraint(
            "accounts_per_series BETWEEN 1 AND 100",
            name="ck_delivery_auto_rule_accounts",
        ),
        CheckConstraint(
            "max_videos_per_series BETWEEN 1 AND 500",
            name="ck_delivery_auto_rule_videos",
        ),
        CheckConstraint(
            "(cost_min IS NULL AND cost_max IS NULL) OR "
            "(cost_min IS NOT NULL AND cost_max IS NOT NULL AND cost_min >= 0 AND cost_min <= cost_max)",
            name="ck_delivery_auto_rule_cost",
        ),
        CheckConstraint(
            "(roi_min IS NULL AND roi_max IS NULL) OR "
            "(roi_min IS NOT NULL AND roi_max IS NOT NULL AND roi_min >= 0 AND roi_min <= roi_max)",
            name="ck_delivery_auto_rule_roi",
        ),
        CheckConstraint(
            "(publish_start IS NULL AND publish_end IS NULL) OR "
            "(publish_start IS NOT NULL AND publish_end IS NOT NULL AND publish_start <= publish_end)",
            name="ck_delivery_auto_rule_publish",
        ),
        Index(
            "uq_delivery_auto_rule_owner_name_alive",
            "pitcher_user_id",
            "charge_mode",
            "name",
            unique=True,
            postgresql_where=text("is_deleted = 0"),
        ),
        Index(
            "ix_delivery_auto_rule_pitcher_charge",
            "pitcher_user_id",
            "charge_mode",
            postgresql_where=text("is_deleted = 0"),
        ),
        {"comment": "漫剧标准投放自动规则。到点经假客户端确认提交，不直连开放平台。"},
    )

    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="规则名称。按类型和时间生成")
    rule_kind: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="publish",
        server_default=text("'publish'"),
        comment="publish 按上架时间、cost 按短剧消耗",
    )
    theater: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="番茄漫剧",
        server_default=text("'番茄漫剧'"),
        comment="剧场。固定番茄漫剧",
    )
    charge_mode: Mapped[str] = mapped_column(
        String(8), nullable=False, comment="从模板抄来的收费模式"
    )
    template_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("delivery_template.id", ondelete="RESTRICT"),
        nullable=False,
        comment="批量模板",
    )
    pitcher_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="创建规则的投手，列表只看自己的",
    )
    accounts_per_series: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, server_default=text("3"), comment="每部剧使用的账户数，默认 3"
    )
    max_videos_per_series: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=200,
        server_default=text("200"),
        comment="每部剧最多取多少条视频，默认 200",
    )
    schedule_start: Mapped[datetime | None] = mapped_column(
        _TS, nullable=True, comment="预约执行时间。空表示立即执行"
    )
    schedule_end: Mapped[datetime | None] = mapped_column(
        _TS, nullable=True, comment="不使用。可空，也可与开始相同"
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="开关。关掉后不执行",
    )
    ran_at: Mapped[datetime | None] = mapped_column(
        _TS, nullable=True, comment="当前这次立即或预约已经执行的时间。空表示还没跑"
    )
    cost_min: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, comment="短剧消耗下限，单位元。空表示不限"
    )
    cost_max: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, comment="短剧消耗上限，单位元"
    )
    roi_min: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True, comment="短剧回收率下限。空表示不限"
    )
    roi_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True, comment="短剧回收率上限")
    publish_start: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="短剧上架日期下限。筛 manhua_series.publish_time，不是报表时间"
    )
    publish_end: Mapped[date | None] = mapped_column(Date, nullable=True, comment="短剧上架日期上限")
    no_bid_only: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="真则只针对最大转化。执行时模板须为 NO_BID",
    )


class DeliveryAutoRuleSeries(BaseModel):
    """规则选中的短剧。可多选。"""

    __tablename__ = "delivery_auto_rule_series"
    __table_args__ = (
        Index("uq_delivery_auto_rule_series_pair", "rule_id", "series_id", unique=True),
        Index("ix_delivery_auto_rule_series_rule", "rule_id", "sort_order"),
        {"comment": "自动规则的短剧。剧场不另存。"},
    )

    rule_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("delivery_auto_rule.id", ondelete="CASCADE"),
        nullable=False,
        comment="规则",
    )
    series_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("manhua_series.id", ondelete="RESTRICT"),
        nullable=False,
        comment="短剧",
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="请求里的顺序，从 0 起")


class DeliveryAutoRuleRun(BaseModel):
    """一条自动规则对一部短剧的执行结果。由执行器写入，没有手建接口。"""

    __tablename__ = "delivery_auto_rule_run"
    __table_args__ = (
        CheckConstraint(
            "status IN ('success', 'failed')",
            name="ck_delivery_auto_rule_run_status",
        ),
        CheckConstraint("char_length(series_name) >= 1", name="ck_delivery_auto_rule_run_series"),
        Index("ix_delivery_auto_rule_run_rule", "rule_id", "id"),
        {"comment": "标准自动规则的执行结果。一部短剧一行。"},
    )

    rule_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("delivery_auto_rule.id", ondelete="CASCADE"),
        nullable=False,
        comment="规则",
    )
    series_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("manhua_series.id", ondelete="RESTRICT"),
        nullable=True,
        comment="短剧。规则级失败可空",
    )
    series_name: Mapped[str] = mapped_column(String(512), nullable=False, comment="执行当时的短剧名称")
    status: Mapped[str] = mapped_column(String(16), nullable=False, comment="success 成功、failed 失败")
    reason: Mapped[str] = mapped_column(
        String(2000), nullable=False, default="", server_default="", comment="失败原因。成功为空"
    )
    draft_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("delivery_task_draft.id", ondelete="SET NULL"),
        nullable=True,
        comment="生成的草稿。失败且没建草稿时为空",
    )
    executed_at: Mapped[datetime] = mapped_column(_TS, nullable=False, comment="执行时间")


class DeliveryProductSnapshot(BaseModel):
    """可被标准模板抄走的产品信息。没有厂商同步。"""

    __tablename__ = "delivery_product_snapshot"
    __table_args__ = (
        CheckConstraint("char_length(name) >= 1", name="ck_delivery_product_snapshot_name"),
        CheckConstraint("char_length(product_name) >= 1", name="ck_delivery_product_snapshot_product"),
        CheckConstraint(
            "product_image_id LIKE 'img-%'",
            name="ck_delivery_product_snapshot_image",
        ),
        Index(
            "uq_delivery_product_snapshot_name_alive",
            "name",
            unique=True,
            postgresql_where=text("is_deleted = 0"),
        ),
        {"comment": "标准模板可复制的产品快照。名称、主图、卖点、行动号召。"},
    )

    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="快照名称")
    product_name: Mapped[str] = mapped_column(String(20), nullable=False, comment="产品名称，最多 20 字")
    product_image_id: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="产品主图 id，img- 前缀"
    )
    selling_points: Mapped[list[str]] = mapped_column(
        ARRAY(String(20)),
        nullable=False,
        default=list,
        server_default=text("ARRAY[]::varchar[]"),
        comment="产品卖点",
    )
    call_to_action_buttons: Mapped[list[str]] = mapped_column(
        ARRAY(String(20)),
        nullable=False,
        default=list,
        server_default=text("ARRAY[]::varchar[]"),
        comment="行动号召",
    )
