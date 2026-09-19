"""codigo de verificacion de correo para usuarios cliente

Revision ID: 0007_verificacion_correo
Revises: 0006_rls_policies
Create Date: 2026-09-18
"""
import sqlalchemy as sa
from alembic import op

revision = "0007_verificacion_correo"
down_revision = "0006_rls_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("codigo_verificacion", sa.String(6), nullable=True))
    op.add_column(
        "usuarios", sa.Column("codigo_verificacion_expira", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("usuarios", "codigo_verificacion_expira")
    op.drop_column("usuarios", "codigo_verificacion")
