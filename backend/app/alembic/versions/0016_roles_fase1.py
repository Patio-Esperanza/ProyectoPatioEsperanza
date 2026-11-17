"""roles adicionales fase 1 (despachador, operador_grua, cuadrilla)

Revision ID: 0016_roles_fase1
Revises: 0015_inspecciones_y_evidencias
Create Date: 2026-11-17
"""
import sqlalchemy as sa
from alembic import op

revision = "0016_roles_fase1"
down_revision = "0015_inspecciones_y_evidencias"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # Use a separate connection with AUTOCOMMIT since ALTER TYPE ... ADD VALUE
    # cannot be executed inside a transaction block in PostgreSQL
    conn = bind.engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    try:
        conn.execute(sa.text("ALTER TYPE rol_usuario ADD VALUE IF NOT EXISTS 'despachador'"))
        conn.execute(sa.text("ALTER TYPE rol_usuario ADD VALUE IF NOT EXISTS 'operador_grua'"))
        conn.execute(sa.text("ALTER TYPE rol_usuario ADD VALUE IF NOT EXISTS 'cuadrilla'"))
    finally:
        conn.close()


def downgrade() -> None:
    # PostgreSQL does not support dropping enum values easily
    pass