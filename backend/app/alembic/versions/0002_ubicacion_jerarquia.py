"""ubicacion jerarquia

Revision ID: 0002_ubicacion_jerarquia
Revises: 0001_baseline
Create Date: 2026-09-14
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_ubicacion_jerarquia"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

tipo_contenedor = postgresql.ENUM("lleno", "vacio", name="tipo_contenedor")
tipo_contenedor_columna = postgresql.ENUM(
    "lleno", "vacio", name="tipo_contenedor", create_type=False
)


def upgrade() -> None:
    tipo_contenedor.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "patios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False, unique=True),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="America/Mexico_City"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "carriles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patios.id"), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tipo_teorico", tipo_contenedor_columna, nullable=True),
        sa.UniqueConstraint("patio_id", "codigo", name="uq_carril_patio_codigo"),
    )
    op.create_table(
        "tramos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("carril_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("carriles.id"), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("carril_id", "codigo", name="uq_tramo_carril_codigo"),
    )
    op.create_table(
        "tiras",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tramo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tramos.id"), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("tramo_id", "codigo", name="uq_tira_tramo_codigo"),
    )
    op.create_table(
        "ubicaciones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tira_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tiras.id"), nullable=False),
        sa.Column("nivel", sa.SmallInteger(), nullable=False),
        sa.Column("codigo", sa.String(30), nullable=False),
        sa.Column("capacidad_peso_kg", sa.Integer(), nullable=False, server_default="30000"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("tira_id", "nivel", name="uq_ubicacion_tira_nivel"),
        sa.CheckConstraint("nivel BETWEEN 1 AND 5", name="ck_ubicacion_nivel_1_5"),
    )


def downgrade() -> None:
    op.drop_table("ubicaciones")
    op.drop_table("tiras")
    op.drop_table("tramos")
    op.drop_table("carriles")
    op.drop_table("patios")
    tipo_contenedor.drop(op.get_bind())
