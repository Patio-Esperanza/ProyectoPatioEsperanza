"""indice varchar_pattern_ops en numero_contenedor

Revision ID: 0017_fase2_buscar
Revises: 0016_roles_fase1
Create Date: 2026-11-17
"""
import sqlalchemy as sa
from alembic import op

revision = "0017_fase2_buscar"
down_revision = "0016_roles_fase1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_contenedores_numero_pattern ON contenedores (numero_contenedor varchar_pattern_ops);"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS idx_contenedores_numero_pattern;"))
