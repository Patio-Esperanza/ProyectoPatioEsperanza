"""sello de seguridad del contenedor

Revision ID: 0014_sellos_contenedor
Revises: 0013_hora_reportes_a_tz_mexico
Create Date: 2026-10-09

La columna es nullable a propósito. `NULL` significa "este contenedor no trae
sello", y la interfaz muestra entonces la leyenda "S/N". Las filas que ya
existen quedan en `NULL`, que es lo correcto: nadie capturó su sello, así que
no hay dato que inventar.
"""
import sqlalchemy as sa
from alembic import op

revision = "0014_sellos_contenedor"
down_revision = "0013_hora_reportes_a_tz_mexico"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contenedores", sa.Column("sellos", sa.String(120), nullable=True))


def downgrade() -> None:
    op.drop_column("contenedores", "sellos")
