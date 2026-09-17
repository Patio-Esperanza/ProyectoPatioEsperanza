"""contenedor movimiento

Revision ID: 0005_contenedor_movimiento
Revises: 0004_auditoria_rol_app
Create Date: 2026-09-14
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_contenedor_movimiento"
down_revision = "0004_auditoria_rol_app"
branch_labels = None
depends_on = None

tamano_contenedor = postgresql.ENUM("20", "40", "45", name="tamano_contenedor")
estado_contenedor = postgresql.ENUM(
    "solicitud_ingreso", "qr_ingreso_emitido", "en_porteria", "ingresado", "ubicado",
    "en_estadia", "en_servicio_especial", "solicitud_salida", "qr_salida_emitido",
    "en_porteria_salida", "despachado", "rechazado",
    name="estado_contenedor",
)
tipo_movimiento = postgresql.ENUM("ingreso", "reubicacion", "servicio", "salida", name="tipo_movimiento")

tamano_contenedor_column = postgresql.ENUM("20", "40", "45", name="tamano_contenedor", create_type=False)
estado_contenedor_column = postgresql.ENUM(
    "solicitud_ingreso", "qr_ingreso_emitido", "en_porteria", "ingresado", "ubicado",
    "en_estadia", "en_servicio_especial", "solicitud_salida", "qr_salida_emitido",
    "en_porteria_salida", "despachado", "rechazado",
    name="estado_contenedor",
    create_type=False,
)
tipo_movimiento_column = postgresql.ENUM(
    "ingreso", "reubicacion", "servicio", "salida", name="tipo_movimiento", create_type=False
)


def upgrade() -> None:
    tamano_contenedor.create(op.get_bind())
    estado_contenedor.create(op.get_bind())
    tipo_movimiento.create(op.get_bind())

    op.create_table(
        "contenedores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("numero_contenedor", sa.String(11), nullable=False),
        sa.Column("tipo", postgresql.ENUM(name="tipo_contenedor", create_type=False), nullable=False),
        sa.Column("tamano", tamano_contenedor_column, nullable=False),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clientes.id"), nullable=True),
        sa.Column("patio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patios.id"), nullable=False),
        sa.Column("ubicacion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ubicaciones.id"), nullable=True),
        sa.Column("estado", estado_contenedor_column, nullable=False),
        sa.Column("peso_kg", sa.Integer(), nullable=False),
        sa.Column("fecha_estimada_salida", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "uq_contenedor_ubicacion_activa",
        "contenedores",
        ["ubicacion_id"],
        unique=True,
        postgresql_where=sa.text("ubicacion_id IS NOT NULL"),
    )

    op.create_table(
        "movimientos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("contenedor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contenedores.id"), nullable=False),
        sa.Column("patio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patios.id"), nullable=False),
        sa.Column("tipo", tipo_movimiento_column, nullable=False),
        sa.Column("ubicacion_origen_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ubicaciones.id"), nullable=True),
        sa.Column("ubicacion_destino_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ubicaciones.id"), nullable=True),
        sa.Column("operador_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("override_manual", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("score_sugerido", sa.Float(), nullable=True),
        sa.Column("score_elegido", sa.Float(), nullable=True),
        sa.Column("motivo_override", sa.Text(), nullable=True),
    )
    op.create_index("ix_movimiento_contenedor_ts", "movimientos", ["contenedor_id", "ts"])

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON contenedores, movimientos TO patio_app;")


def downgrade() -> None:
    op.drop_table("movimientos")
    op.drop_index("uq_contenedor_ubicacion_activa", table_name="contenedores")
    op.drop_table("contenedores")
    tipo_movimiento.drop(op.get_bind())
    estado_contenedor.drop(op.get_bind())
    tamano_contenedor.drop(op.get_bind())
