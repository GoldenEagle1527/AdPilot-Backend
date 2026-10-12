"""标准自动规则到点执行、产品快照，以及端原生任务的执行中/完成。

Revision ID: 20261009_05
Revises: 20261009_04
Create Date: 2026-10-09

自动规则增加开关和已执行时间。执行结果按短剧落一行。
产品快照给标准模板抄产品名称、主图、卖点和行动号召。
端原生任务状态在 saved 之外允许 running（执行中）和 done（完成）。
不插入假规则，也不插入执行记录。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261009_05"
down_revision: Union[str, None] = "20261009_04"
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
        "delivery_auto_rule",
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="开关。关掉后不执行",
        ),
    )
    op.add_column(
        "delivery_auto_rule",
        sa.Column(
            "ran_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="当前这次立即或预约已经执行的时间。空表示还没跑",
        ),
    )
    op.create_table(
        "delivery_auto_rule_run",
        *_common(),
        sa.Column("rule_id", sa.Integer(), nullable=False, comment="规则"),
        sa.Column("series_id", sa.Integer(), nullable=True, comment="短剧。规则级失败可空"),
        sa.Column("series_name", sa.String(length=512), nullable=False, comment="执行当时的短剧名称"),
        sa.Column("status", sa.String(length=16), nullable=False, comment="success 成功、failed 失败"),
        sa.Column("reason", sa.String(length=2000), nullable=False, server_default="", comment="失败原因。成功为空"),
        sa.Column("draft_id", sa.Integer(), nullable=True, comment="生成的草稿"),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False, comment="执行时间"),
        sa.CheckConstraint("status IN ('success', 'failed')", name="ck_delivery_auto_rule_run_status"),
        sa.CheckConstraint("char_length(series_name) >= 1", name="ck_delivery_auto_rule_run_series"),
        sa.ForeignKeyConstraint(["rule_id"], ["delivery_auto_rule.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["series_id"], ["manhua_series.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["draft_id"], ["delivery_task_draft.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_delivery_auto_rule_run_rule", "delivery_auto_rule_run", ["rule_id", "id"])
    op.create_table(
        "delivery_product_snapshot",
        *_common(),
        sa.Column("name", sa.String(length=128), nullable=False, comment="快照名称"),
        sa.Column("product_name", sa.String(length=20), nullable=False, comment="产品名称，最多 20 字"),
        sa.Column("product_image_id", sa.String(length=64), nullable=False, comment="产品主图 id，img- 前缀"),
        sa.Column(
            "selling_points",
            sa.ARRAY(sa.String(length=20)),
            nullable=False,
            server_default=sa.text("ARRAY[]::varchar[]"),
            comment="产品卖点",
        ),
        sa.Column(
            "call_to_action_buttons",
            sa.ARRAY(sa.String(length=20)),
            nullable=False,
            server_default=sa.text("ARRAY[]::varchar[]"),
            comment="行动号召",
        ),
        sa.CheckConstraint("char_length(name) >= 1", name="ck_delivery_product_snapshot_name"),
        sa.CheckConstraint("char_length(product_name) >= 1", name="ck_delivery_product_snapshot_product"),
        sa.CheckConstraint("product_image_id LIKE 'img-%'", name="ck_delivery_product_snapshot_image"),
    )
    op.create_index(
        "uq_delivery_product_snapshot_name_alive",
        "delivery_product_snapshot",
        ["name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = 0"),
    )
    op.drop_constraint("ck_uni_native_task_status", "uni_native_task", type_="check")
    op.create_check_constraint(
        "ck_uni_native_task_status",
        "uni_native_task",
        "status IN ('saved', 'running', 'done')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_uni_native_task_status", "uni_native_task", type_="check")
    op.create_check_constraint("ck_uni_native_task_status", "uni_native_task", "status = 'saved'")
    op.drop_index("uq_delivery_product_snapshot_name_alive", table_name="delivery_product_snapshot")
    op.drop_table("delivery_product_snapshot")
    op.drop_index("ix_delivery_auto_rule_run_rule", table_name="delivery_auto_rule_run")
    op.drop_table("delivery_auto_rule_run")
    op.drop_column("delivery_auto_rule", "ran_at")
    op.drop_column("delivery_auto_rule", "is_enabled")
