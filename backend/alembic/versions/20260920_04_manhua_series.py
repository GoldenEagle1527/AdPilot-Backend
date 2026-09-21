"""manhua series cache from Changdu.

Revision ID: 20260920_04
Revises: 20260920_03
Create Date: 2026-09-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260920_04"
down_revision: Union[str, None] = "20260920_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "manhua_series",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("thumb_url", sa.String(length=1024), nullable=False, server_default=""),
        sa.Column("book_id", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("playlet_id", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("book_name", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("episode_amount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gender", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("category_text", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("publish_status", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("publish_time", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("estimate_publish_time", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("permission_status", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("create_time", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("douyin_nick_name", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("single_price", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("abstract", sa.String(length=4000), nullable=False, server_default=""),
        sa.Column("delivery_status", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("playlet_id", "book_name", name="uq_manhua_series_playlet_book"),
    )


def downgrade() -> None:
    op.drop_table("manhua_series")
