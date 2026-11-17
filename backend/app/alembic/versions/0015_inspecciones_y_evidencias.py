"""Inspecciones, evidencias, pin de salida y indice unico activo para contenedores

Revision ID: 0015_inspecciones_y_evidencias
Revises: 0014_sellos_contenedor
Create Date: 2026-11-17
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0015_inspecciones_y_evidencias"
down_revision = "0014_sellos_contenedor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Agregar columnas de pin de salida y fecha de salida a contenedores
    op.add_column("contenedores", sa.Column("pin_salida_hash", sa.String(255), nullable=True))
    op.add_column("contenedores", sa.Column("pin_salida_intentos", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("contenedores", sa.Column("fecha_salida", sa.DateTime(timezone=True), nullable=True))

    # Índice único parcial para contenedores activos (estado != despachado y estado != rechazado)
    op.create_index(
        "uq_contenedor_activo",
        "contenedores",
        ["numero_contenedor"],
        unique=True,
        postgresql_where=sa.text("estado != 'despachado' AND estado != 'rechazado'"),
    )

    # Check constraint: un contenedor despachado no puede tener ubicación actual
    op.create_check_constraint(
        "ck_despachado_sin_ubicacion",
        "contenedores",
        "estado != 'despachado' OR ubicacion_id IS NULL",
    )

    # Crear tabla inspecciones
    op.create_table(
        "inspecciones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("contenedor_id", UUID(as_uuid=True), sa.ForeignKey("contenedores.id"), nullable=False),
        sa.Column("movimiento_id", UUID(as_uuid=True), sa.ForeignKey("movimientos.id"), nullable=True),
        sa.Column("placas", sa.String(20), nullable=True),
        sa.Column("operador", sa.String(100), nullable=True),
        sa.Column("sellos", sa.String(120), nullable=True),
        sa.Column("danos", JSONB, nullable=True),
        sa.Column("notas", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Crear tabla evidencias
    op.create_table(
        "evidencias",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("contenedor_id", UUID(as_uuid=True), sa.ForeignKey("contenedores.id"), nullable=False),
        sa.Column("inspeccion_id", UUID(as_uuid=True), sa.ForeignKey("inspecciones.id"), nullable=True),
        sa.Column("movimiento_id", UUID(as_uuid=True), sa.ForeignKey("movimientos.id"), nullable=True),
        sa.Column("servicio_contenedor_id", UUID(as_uuid=True), nullable=True),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("tipo", sa.String(50), nullable=False, server_default="ingreso"),
        sa.Column("creado_por", UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("evidencias")
    op.drop_table("inspecciones")
    op.drop_constraint("ck_despachado_sin_ubicacion", "contenedores", type_="check")
    op.drop_index("uq_contenedor_activo", table_name="contenedores")
    op.drop_column("contenedores", "fecha_salida")
    op.drop_column("contenedores", "pin_salida_intentos")
    op.drop_column("contenedores", "pin_salida_hash")
