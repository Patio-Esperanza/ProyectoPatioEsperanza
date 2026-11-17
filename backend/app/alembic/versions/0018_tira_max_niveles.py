"""tira max_niveles

Revision ID: 0018_tira_max_niveles
Revises: 0017_fase2_buscar
Create Date: 2026-11-17
"""
import sqlalchemy as sa
from alembic import op

revision = "0018_tira_max_niveles"
down_revision = "0017_fase2_buscar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tiras",
        sa.Column("max_niveles", sa.SmallInteger(), nullable=False, server_default="5"),
    )


def downgrade() -> None:
    op.drop_column("tiras", "max_niveles")
