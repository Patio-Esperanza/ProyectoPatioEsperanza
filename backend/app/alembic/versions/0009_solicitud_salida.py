"""anticipacion minima por patio y solicitud de salida de contenedores

Revision ID: 0009_solicitud_salida
Revises: 0008_pin_confirmacion
Create Date: 2026-09-19
"""
import sqlalchemy as sa
from alembic import op

revision = "0009_solicitud_salida"
down_revision = "0008_pin_confirmacion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patios",
        sa.Column("anticipacion_minima_horas", sa.Integer(), nullable=False, server_default="24"),
    )
    op.add_column(
        "contenedores", sa.Column("fecha_deseada_salida", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "contenedores", sa.Column("salida_solicitada_en", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("contenedores", "salida_solicitada_en")
    op.drop_column("contenedores", "fecha_deseada_salida")
    op.drop_column("patios", "anticipacion_minima_horas")
