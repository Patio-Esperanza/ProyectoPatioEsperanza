"""crear tabla reportes_programados

Revision ID: 0012_reportes_programados
Revises: 0011_patio_punto_entrada
Create Date: 2026-09-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0012_reportes_programados"
down_revision = "0011_patio_punto_entrada"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reportes_programados",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("tipo_reporte", sa.String(length=50), nullable=False),
        sa.Column("patio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patios.id"), nullable=True),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clientes.id"), nullable=True),
        sa.Column("frecuencia", sa.String(length=20), nullable=False),
        sa.Column("hora", sa.Integer(), nullable=False),
        sa.Column("minuto", sa.Integer(), nullable=False),
        sa.Column("dia_semana", sa.Integer(), nullable=True),
        sa.Column("dia_mes", sa.Integer(), nullable=True),
        sa.Column("destinatarios", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("asunto", sa.String(length=255), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("ultimo_envio", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultimo_estado", sa.String(length=50), nullable=True),
        sa.Column("ultimo_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("reportes_programados")
