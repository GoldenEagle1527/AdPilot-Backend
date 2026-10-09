"""漫剧表列类型对齐模型。

Revision ID: 20261009_03
Revises: 20261009_02
Create Date: 2026-10-09

category_text 从 varchar(128) 放到 varchar(512)，题材串不再被截断。
estimate_publish_time 从 varchar(64) 收成带时区时间。空串变成空。
已有值按北京时间 YYYY-MM-DD HH:MM:SS 解释。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261009_03"
down_revision: Union[str, None] = "20261009_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ESTIMATE_TO_TIMESTAMP = """
CASE
    WHEN estimate_publish_time IS NULL OR btrim(estimate_publish_time) = '' THEN NULL
    ELSE (estimate_publish_time::timestamp AT TIME ZONE 'Asia/Shanghai')
END
"""

_ESTIMATE_TO_TEXT = """
CASE
    WHEN estimate_publish_time IS NULL THEN ''
    ELSE to_char(estimate_publish_time AT TIME ZONE 'Asia/Shanghai', 'YYYY-MM-DD HH24:MI:SS')
END
"""


def upgrade() -> None:
    op.alter_column(
        "manhua_series",
        "category_text",
        existing_type=sa.String(length=128),
        type_=sa.String(length=512),
        existing_nullable=False,
        comment="常读题材，逗号分隔，如 玄幻脑洞,逆袭",
    )
    op.alter_column(
        "manhua_series",
        "estimate_publish_time",
        existing_type=sa.String(length=64),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        nullable=True,
        postgresql_using=_ESTIMATE_TO_TIMESTAMP,
        comment="常读预估可投时间（北京），常读没给为空",
    )


def downgrade() -> None:
    op.alter_column(
        "manhua_series",
        "estimate_publish_time",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.String(length=64),
        existing_nullable=True,
        nullable=False,
        postgresql_using=_ESTIMATE_TO_TEXT,
        comment="常读预估可投时间原串",
    )
    op.alter_column(
        "manhua_series",
        "category_text",
        existing_type=sa.String(length=512),
        type_=sa.String(length=128),
        existing_nullable=False,
        comment="分类文案，如 IAA/IAP，供 tab",
    )
