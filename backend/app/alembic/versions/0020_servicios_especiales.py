"""servicios_catalogo y servicios_contenedor con semilla inicial

Revision ID: 0020_servicios_especiales
Revises: 0019_v_estancias
Create Date: 2026-11-17
"""
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0020_servicios_especiales"
down_revision = "0019_v_estancias"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create servicios_catalogo table
    op.create_table(
        "servicios_catalogo",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("patio_id", UUID(as_uuid=True), sa.ForeignKey("patios.id"), nullable=True),
        sa.Column("codigo", sa.String(10), nullable=False),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("requiere_evidencia", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("bloquea_salida", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requiere_mover", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requiere_unidad_relacionada", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("cliente_puede_solicitar", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("patio_id", "codigo", name="uq_servicio_catalogo_patio_codigo"),
    )

    # 2. Create servicios_contenedor table
    op.create_table(
        "servicios_contenedor",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("contenedor_id", UUID(as_uuid=True), sa.ForeignKey("contenedores.id"), nullable=False),
        sa.Column("servicio_catalogo_id", UUID(as_uuid=True), sa.ForeignKey("servicios_catalogo.id"), nullable=False),
        sa.Column("cliente_id", UUID(as_uuid=True), sa.ForeignKey("clientes.id"), nullable=True),
        sa.Column("estado", sa.Enum("solicitado", "programado", "en_proceso", "terminado", "rechazado", "cancelado", name="estado_servicio"), nullable=False, server_default="solicitado"),
        sa.Column("solicitado_por", UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("asignado_a", UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("realizado_por", UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("programado_para", sa.DateTime(timezone=True), nullable=True),
        sa.Column("solicitado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("iniciado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("terminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("unidad_relacionada_tipo", sa.Enum("contenedor", "caja_seca", name="unidad_relacionada_tipo"), nullable=True),
        sa.Column("contenedor_relacionado_id", UUID(as_uuid=True), sa.ForeignKey("contenedores.id"), nullable=True),
        sa.Column("unidad_relacionada_ref", sa.String(100), nullable=True),
    )

    # 3. Seed initial catalog data
    op.execute(
        """
        INSERT INTO servicios_catalogo (patio_id, codigo, nombre, descripcion, requiere_evidencia, bloquea_salida, requiere_mover, requiere_unidad_relacionada, cliente_puede_solicitar, activo)
        VALUES
            (NULL, 'TRA', 'Traspaleo', 'Traslado de carga entre contenedores', true, true, false, true, true, true),
            (NULL, 'REA', 'Reacomodo', 'Reacomodo de carga dentro del contenedor', true, true, false, false, true, true),
            (NULL, 'DES', 'Desempalme', 'Separación de contenedores apilados', true, true, false, false, true, true),
            (NULL, 'EMP', 'Empalme', 'Apilamiento de contenedores', true, true, false, false, true, true)
        ON CONFLICT (patio_id, codigo) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_table("servicios_contenedor")
    op.drop_table("servicios_catalogo")
    op.execute("DROP TYPE IF EXISTS estado_servicio")
    op.execute("DROP TYPE IF EXISTS unidad_relacionada_tipo")
