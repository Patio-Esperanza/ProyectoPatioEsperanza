"""punto de entrada del patio para el mapa

Revision ID: 0011_patio_punto_entrada
Revises: 0010_rls_fail_closed
Create Date: 2026-09-22
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011_patio_punto_entrada"
down_revision = "0010_rls_fail_closed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patios",
        sa.Column("ubicacion_entrada_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    # La llave cierra un ciclo: patios -> ubicaciones -> tiras -> tramos -> carriles -> patios.
    # Postgres lo acepta porque la restriccion se agrega despues de que las dos tablas existen.
    op.create_foreign_key(
        "fk_patio_ubicacion_entrada",
        "patios",
        "ubicaciones",
        ["ubicacion_entrada_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_patio_ubicacion_entrada", "patios", type_="foreignkey")
    op.drop_column("patios", "ubicacion_entrada_id")
