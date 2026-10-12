"""产品清单：广告预算、推广链、预约提交、全域失败态、端原生机器人。

Revision ID: 20261009_06
Revises: 20261009_05
Create Date: 2026-10-09

服务商同步没有远端接口，未接入厂商。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261009_06"
down_revision: Union[str, None] = "20261009_05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _common() -> list[sa.Column]:
    """和 BaseModel 对齐的公共列。"""
    return [
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True, comment="库内自增主键"),
        sa.Column("is_deleted", sa.Integer(), nullable=False, server_default="0", comment="是否删除：0 否、1 是"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="删除时间，未删为空"),
        sa.Column(
            "created_date",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="创建时间（北京）",
        ),
        sa.Column(
            "updated_date",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="更新时间（北京）",
        ),
    ]


def upgrade() -> None:
    op.add_column(
        "delivery_template",
        sa.Column("ad_budget", sa.Numeric(12, 2), nullable=True, comment="广告预算，单位元。仅标准模板"),
    )
    op.add_column(
        "delivery_task_draft",
        sa.Column("promotion_link_id", sa.Integer(), nullable=True, comment="选中的剧场推广链"),
    )
    op.add_column(
        "delivery_task_draft",
        sa.Column("link_name", sa.String(64), nullable=True, comment="推广链接名称"),
    )
    op.add_column(
        "delivery_task_draft",
        sa.Column("series_short_name", sa.String(32), nullable=True, comment="短剧简称"),
    )
    op.add_column(
        "delivery_task_draft",
        sa.Column("product_book_name", sa.String(512), nullable=True, comment="非本剧商品剧名"),
    )
    op.add_column(
        "delivery_task_draft",
        sa.Column(
            "video_order",
            sa.String(16),
            nullable=False,
            server_default=sa.text("'upload'"),
            comment="视频顺序",
        ),
    )
    op.add_column(
        "delivery_task_draft",
        sa.Column(
            "batch_titles",
            postgresql.ARRAY(sa.String(55)),
            nullable=False,
            server_default=sa.text("ARRAY[]::varchar[]"),
            comment="批量粘贴标题",
        ),
    )
    op.add_column(
        "delivery_task_draft",
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True, comment="确认提交时间"),
    )
    op.add_column(
        "delivery_auto_rule",
        sa.Column(
            "rule_kind",
            sa.String(16),
            nullable=False,
            server_default=sa.text("'publish'"),
            comment="publish 或 cost",
        ),
    )
    op.add_column(
        "delivery_auto_rule",
        sa.Column(
            "theater",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'番茄漫剧'"),
            comment="剧场",
        ),
    )
    op.add_column(
        "uni_native_task",
        sa.Column("failure_reason", sa.Text(), nullable=True, comment="失败原因"),
    )
    op.add_column(
        "uni_native_task",
        sa.Column(
            "materials_uploaded",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="素材是否上传完成",
        ),
    )
    op.drop_constraint("ck_uni_native_task_status", "uni_native_task", type_="check")
    op.create_check_constraint(
        "ck_uni_native_task_status",
        "uni_native_task",
        "status IN ('saved', 'running', 'done', 'failed')",
    )
    op.add_column(
        "uni_robot_rule",
        sa.Column("pitcher_user_id", sa.Integer(), nullable=True, comment="规则所属投手"),
    )
    op.create_foreign_key(
        "fk_uni_robot_rule_pitcher",
        "uni_robot_rule",
        "users",
        ["pitcher_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    from app.modules.standard_delivery.model import _TEMPLATE_SHAPE

    op.drop_constraint("ck_delivery_template_mode_shape", "delivery_template", type_="check")
    op.create_check_constraint("ck_delivery_template_mode_shape", "delivery_template", _TEMPLATE_SHAPE)
    op.create_table(
        "standard_native_robot_rule",
        *_common(),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("charge_mode", sa.String(8), nullable=False),
        sa.Column("rule_kind", sa.String(32), nullable=False),
        sa.Column("schedule_kind", sa.String(16), nullable=False),
        sa.Column("schedule_hour", sa.Integer(), nullable=True),
        sa.Column("schedule_minute", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("pitcher_user_id", sa.Integer(), nullable=False),
        sa.Column("platform_id", sa.Integer(), nullable=True),
        sa.Column("accounts_per_series", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("max_videos_per_series", sa.Integer(), nullable=False, server_default="200"),
        sa.Column("stat_span", sa.String(16), nullable=True),
        sa.Column("cost_min", sa.Numeric(12, 2), nullable=True),
        sa.Column("cost_max", sa.Numeric(12, 2), nullable=True),
        sa.Column("recovery_min", sa.Numeric(10, 4), nullable=True),
        sa.Column("recovery_max", sa.Numeric(10, 4), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_ran_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("charge_mode IN ('IAA', 'IAP')", name="ck_std_native_robot_charge"),
        sa.CheckConstraint("rule_kind IN ('nb', 'drama', 'promotion_link')", name="ck_std_native_robot_kind"),
        sa.CheckConstraint("schedule_kind IN ('hourly', 'period')", name="ck_std_native_robot_schedule"),
        sa.ForeignKeyConstraint(["template_id"], ["delivery_template.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pitcher_user_id"], ["users.id"], ondelete="RESTRICT"),
    )


def downgrade() -> None:
    op.drop_table("standard_native_robot_rule")
    op.drop_constraint("fk_uni_robot_rule_pitcher", "uni_robot_rule", type_="foreignkey")
    op.drop_column("uni_robot_rule", "pitcher_user_id")
    op.drop_constraint("ck_uni_native_task_status", "uni_native_task", type_="check")
    op.create_check_constraint(
        "ck_uni_native_task_status",
        "uni_native_task",
        "status IN ('saved', 'running', 'done')",
    )
    op.drop_column("uni_native_task", "materials_uploaded")
    op.drop_column("uni_native_task", "failure_reason")
    op.drop_column("delivery_auto_rule", "theater")
    op.drop_column("delivery_auto_rule", "rule_kind")
    op.drop_column("delivery_task_draft", "submitted_at")
    op.drop_column("delivery_task_draft", "batch_titles")
    op.drop_column("delivery_task_draft", "video_order")
    op.drop_column("delivery_task_draft", "product_book_name")
    op.drop_column("delivery_task_draft", "series_short_name")
    op.drop_column("delivery_task_draft", "link_name")
    op.drop_column("delivery_task_draft", "promotion_link_id")
    import importlib

    previous = importlib.import_module("alembic.versions.20261009_02_template_audience_gender_age")
    op.drop_constraint("ck_delivery_template_mode_shape", "delivery_template", type_="check")
    op.create_check_constraint("ck_delivery_template_mode_shape", "delivery_template", previous._NEW_SHAPE)
    op.drop_column("delivery_template", "ad_budget")
