"""pin de confirmacion de 4 digitos para contenedores

Revision ID: 0008_pin_confirmacion
Revises: 0007_verificacion_correo
Create Date: 2026-09-19
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008_pin_confirmacion"
down_revision = "0007_verificacion_correo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contenedores", sa.Column("pin_confirmacion", sa.String(4), nullable=True))
    op.add_column(
        "contenedores", sa.Column("pin_verificado_en", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "contenedores",
        sa.Column(
            "pin_verificado_por",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("contenedores", "pin_verificado_por")
    op.drop_column("contenedores", "pin_verificado_en")
    op.drop_column("contenedores", "pin_confirmacion")
