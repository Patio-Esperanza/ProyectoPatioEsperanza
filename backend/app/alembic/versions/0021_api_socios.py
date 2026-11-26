"""api_socios: credenciales_socio, eventos_socio y extensiones en contenedores y clientes

Revision ID: 0021_api_socios
Revises: 0020_servicios_especiales
Create Date: 2026-11-24
"""
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB

revision = "0021_api_socios"
down_revision = "0020_servicios_especiales"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create credenciales_socio table
    op.create_table(
        "credenciales_socio",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("cliente_id", UUID(as_uuid=True), sa.ForeignKey("clientes.id"), nullable=True),
        sa.Column("prefijo", sa.String(8), unique=True, nullable=False, index=True),
        sa.Column("secreto_hash", sa.String(255), nullable=False),
        sa.Column("patios_permitidos", ARRAY(UUID(as_uuid=True)), nullable=False, server_default="{}"),
        sa.Column("webhook_url", sa.String(500), nullable=True),
        sa.Column("webhook_secreto", sa.String(255), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("ultimo_uso_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # 2. Add alta_por_socio to clientes
    op.add_column("clientes", sa.Column("alta_por_socio", sa.Boolean(), nullable=False, server_default="false"))

    # 3. Add socio columns to contenedores
    op.add_column("contenedores", sa.Column("origen", sa.String(50), nullable=True))
    op.add_column("contenedores", sa.Column("credencial_socio_id", UUID(as_uuid=True), sa.ForeignKey("credenciales_socio.id"), nullable=True))
    op.add_column("contenedores", sa.Column("idempotency_key", sa.String(100), nullable=True))
    op.add_column("contenedores", sa.Column("referencia_externa", sa.String(100), nullable=True))
    op.add_column("contenedores", sa.Column("datos_aduana", JSONB(), nullable=True))
    op.add_column("contenedores", sa.Column("transporte_esperado", JSONB(), nullable=True))
    op.add_column("contenedores", sa.Column("peso_por_confirmar", sa.Boolean(), nullable=False, server_default="false"))

    # 4. Unique idempotency index per partner credential
    op.create_index(
        "uq_contenedor_socio_idempotency",
        "contenedores",
        ["credencial_socio_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    # 5. Create eventos_socio table
    op.create_table(
        "eventos_socio",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("credencial_socio_id", UUID(as_uuid=True), sa.ForeignKey("credenciales_socio.id"), nullable=False),
        sa.Column("contenedor_id", UUID(as_uuid=True), sa.ForeignKey("contenedores.id"), nullable=False),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="pendiente"),
        sa.Column("intentos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("siguiente_intento_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("ultimo_error", sa.Text(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("eventos_socio")
    op.drop_index("uq_contenedor_socio_idempotency", table_name="contenedores")
    op.drop_column("contenedores", "peso_por_confirmar")
    op.drop_column("contenedores", "transporte_esperado")
    op.drop_column("contenedores", "datos_aduana")
    op.drop_column("contenedores", "referencia_externa")
    op.drop_column("contenedores", "idempotency_key")
    op.drop_column("contenedores", "credencial_socio_id")
    op.drop_column("contenedores", "origen")
    op.drop_column("clientes", "alta_por_socio")
    op.drop_table("credenciales_socio")
