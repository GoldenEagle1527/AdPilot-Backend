"""确认提交后留下巨量项目 id 和广告 id，报表按它们回到短剧、投手、收费模式和面板。

Revision ID: 20261013_01
Revises: 20261012_05
Create Date: 2026-10-13

标准投放：账户行加 ocean_project_id；新建 delivery_task_project（一户一项目，付费按面板一面板一项目）
和 delivery_task_promotion（一个项目下的多条广告）。
端原生：账户行加 ocean_promotion_id。
已提交的旧数据不回填，编号为空、面板为空串。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261013_01"
down_revision: Union[str, None] = "20261012_05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _base_columns() -> list[sa.Column]:
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
        "delivery_task_account",
        sa.Column(
            "ocean_project_id",
            sa.BigInteger(),
            nullable=True,
            comment="巨量项目 id。本户只建一个项目时写这里。付费按面板拆成多个项目时为空，看 delivery_task_project",
        ),
    )
    op.create_table(
        "delivery_task_project",
        *_base_columns(),
        sa.Column(
            "task_id",
            sa.Integer(),
            sa.ForeignKey("delivery_task_draft.id", ondelete="CASCADE"),
            nullable=False,
            comment="草稿。短剧、投手、收费模式从草稿取",
        ),
        sa.Column(
            "advertiser_account_id",
            sa.Integer(),
            sa.ForeignKey("advertiser_account.id", ondelete="RESTRICT"),
            nullable=False,
            comment="广告主行",
        ),
        sa.Column(
            "bid_panel",
            sa.String(length=64),
            nullable=False,
            server_default="",
            comment="这个项目对应的一个出价面板。免费或模板没有面板时为空串",
        ),
        sa.Column("ocean_project_id", sa.BigInteger(), nullable=False, comment="巨量项目 id。不是本表自增主键"),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            comment="本草稿内的建项目顺序，从 0 起。先按账户，再按面板",
        ),
        comment="标准投放提交后建出的巨量项目。免费或没有面板时一户一行，面板为空串。",
    )
    op.create_index("uq_delivery_task_project_ocean", "delivery_task_project", ["ocean_project_id"], unique=True)
    op.create_index("ix_delivery_task_project_task", "delivery_task_project", ["task_id", "sort_order"])
    op.create_index("ix_delivery_task_project_advertiser", "delivery_task_project", ["advertiser_account_id"])
    op.create_table(
        "delivery_task_promotion",
        *_base_columns(),
        sa.Column(
            "task_project_id",
            sa.Integer(),
            sa.ForeignKey("delivery_task_project.id", ondelete="CASCADE"),
            nullable=False,
            comment="提交时建出的项目行",
        ),
        sa.Column("ocean_promotion_id", sa.BigInteger(), nullable=False, comment="巨量广告 id。不是本表自增主键"),
        sa.Column("sort_order", sa.Integer(), nullable=False, comment="本项目内的建广告顺序，从 0 起"),
        comment="标准投放提交后建出的巨量广告。挂在 delivery_task_project 下。",
    )
    op.create_index(
        "uq_delivery_task_promotion_ocean", "delivery_task_promotion", ["ocean_promotion_id"], unique=True
    )
    op.create_index(
        "ix_delivery_task_promotion_project", "delivery_task_promotion", ["task_project_id", "sort_order"]
    )
    op.add_column(
        "uni_native_task_account",
        sa.Column(
            "ocean_promotion_id",
            sa.BigInteger(),
            nullable=True,
            comment="巨量广告 id。一个项目一条广告。未创建为空",
        ),
    )


def downgrade() -> None:
    op.drop_column("uni_native_task_account", "ocean_promotion_id")
    op.drop_index("ix_delivery_task_promotion_project", table_name="delivery_task_promotion")
    op.drop_index("uq_delivery_task_promotion_ocean", table_name="delivery_task_promotion")
    op.drop_table("delivery_task_promotion")
    op.drop_index("ix_delivery_task_project_advertiser", table_name="delivery_task_project")
    op.drop_index("ix_delivery_task_project_task", table_name="delivery_task_project")
    op.drop_index("uq_delivery_task_project_ocean", table_name="delivery_task_project")
    op.drop_table("delivery_task_project")
    op.drop_column("delivery_task_account", "ocean_project_id")
