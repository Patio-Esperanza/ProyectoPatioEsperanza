"""cliente usuario

Revision ID: 0003_cliente_usuario
Revises: 0002_ubicacion_jerarquia
Create Date: 2026-09-14
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_cliente_usuario"
down_revision = "0002_ubicacion_jerarquia"
branch_labels = None
depends_on = None

tipo_cliente = postgresql.ENUM(
    "agencia_aduanal",
    "importador_exportador",
    "transportista",
    "socio_api",
    name="tipo_cliente",
)
tipo_cliente_columna = postgresql.ENUM(
    "agencia_aduanal",
    "importador_exportador",
    "transportista",
    "socio_api",
    name="tipo_cliente",
    create_type=False,
)
rol_usuario = postgresql.ENUM(
    "cliente",
    "operador",
    "supervisor",
    "admin",
    "guardia",
    "despachador",
    name="rol_usuario",
)
rol_usuario_columna = postgresql.ENUM(
    "cliente",
    "operador",
    "supervisor",
    "admin",
    "guardia",
    "despachador",
    name="rol_usuario",
    create_type=False,
)


def upgrade() -> None:
    tipo_cliente.create(op.get_bind())
    rol_usuario.create(op.get_bind())

    op.create_table(
        "clientes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("razon_social", sa.String(200), nullable=False),
        sa.Column("rfc", sa.String(13), nullable=False, unique=True),
        sa.Column("tipo", tipo_cliente_columna, nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "usuarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clientes.id"), nullable=True),
        sa.Column("tipo", rol_usuario_columna, nullable=False),
        sa.Column("nombre", sa.String(150), nullable=True),
        sa.Column("email", sa.String(200), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("mfa_habilitado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "usuario_patio",
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), primary_key=True),
        sa.Column("patio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patios.id"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("usuario_patio")
    op.drop_table("usuarios")
    op.drop_table("clientes")
    rol_usuario.drop(op.get_bind())
    tipo_cliente.drop(op.get_bind())
