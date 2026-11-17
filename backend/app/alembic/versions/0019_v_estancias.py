"""v_estancias view, inventario_diario table, and stay calculation fields

Revision ID: 0019_v_estancias
Revises: 0018_tira_max_niveles
Create Date: 2026-11-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0019_v_estancias"
down_revision = "0018_tira_max_niveles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add columns
    op.add_column("patios", sa.Column("umbral_estancia_dias", sa.Integer(), nullable=True))
    op.add_column("clientes", sa.Column("dias_libres", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("contenedores", sa.Column("ingresado_en", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_contenedores_ingresado_en", "contenedores", ["ingresado_en"])

    # 2. Backfill ingresado_en from movimientos
    op.execute(
        """
        UPDATE contenedores c
        SET ingresado_en = (
            SELECT MIN(m.ts)
            FROM movimientos m
            WHERE m.contenedor_id = c.id
              AND m.tipo = 'ingreso'
        )
        WHERE c.ingresado_en IS NULL;
        """
    )

    # 3. Create inventario_diario table
    op.create_table(
        "inventario_diario",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("patio_id", UUID(as_uuid=True), sa.ForeignKey("patios.id"), nullable=False),
        sa.Column("contenedor_id", UUID(as_uuid=True), sa.ForeignKey("contenedores.id"), nullable=False),
        sa.Column("cliente_id", UUID(as_uuid=True), sa.ForeignKey("clientes.id"), nullable=True),
        sa.Column("ubicacion_id", UUID(as_uuid=True), sa.ForeignKey("ubicaciones.id"), nullable=True),
        sa.Column("estado", sa.String(50), nullable=False),
        sa.Column("dias_estancia", sa.Integer(), nullable=False),
        sa.UniqueConstraint("fecha", "patio_id", "contenedor_id", name="uq_inventario_diario_fecha_patio_contenedor"),
    )
    op.create_index("ix_inventario_diario_fecha_patio", "inventario_diario", ["fecha", "patio_id"])

    # Enable RLS on inventario_diario
    op.execute("ALTER TABLE inventario_diario ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY inventario_diario_por_patio ON inventario_diario
          USING (
            current_setting('app.rol', true) IS NULL
            OR current_setting('app.rol', true) = 'admin'
            OR current_setting('app.rol', true) = 'cliente'
            OR patio_id::text = ANY(
              string_to_array(coalesce(current_setting('app.patios_asignados', true), ''), ',')
            )
          )
          WITH CHECK (true);
        """
    )

    # 4. Create v_estancias view
    op.execute(
        """
        CREATE VIEW v_estancias AS
        SELECT
            c.id AS contenedor_id,
            c.patio_id,
            c.cliente_id,
            c.ingresado_en,
            c.fecha_salida,
            COALESCE(p.timezone, 'America/Mexico_City') AS zona_horaria,
            GREATEST(1, (
                (COALESCE(c.fecha_salida, CURRENT_TIMESTAMP) AT TIME ZONE COALESCE(p.timezone, 'America/Mexico_City'))::date
                - (c.ingresado_en AT TIME ZONE COALESCE(p.timezone, 'America/Mexico_City'))::date
            ) + 1) AS dias_estancia,
            COALESCE(cl.dias_libres, 0) AS dias_libres,
            GREATEST(0, GREATEST(1, (
                (COALESCE(c.fecha_salida, CURRENT_TIMESTAMP) AT TIME ZONE COALESCE(p.timezone, 'America/Mexico_City'))::date
                - (c.ingresado_en AT TIME ZONE COALESCE(p.timezone, 'America/Mexico_City'))::date
            ) + 1) - COALESCE(cl.dias_libres, 0)) AS dias_cobrables
        FROM contenedores c
        JOIN patios p ON c.patio_id = p.id
        LEFT JOIN clientes cl ON c.cliente_id = cl.id
        WHERE c.ingresado_en IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_estancias;")
    op.execute("DROP POLICY IF EXISTS inventario_diario_por_patio ON inventario_diario;")
    op.execute("ALTER TABLE inventario_diario DISABLE ROW LEVEL SECURITY;")
    op.drop_table("inventario_diario")
    op.drop_index("ix_contenedores_ingresado_en", table_name="contenedores")
    op.drop_column("contenedores", "ingresado_en")
    op.drop_column("clientes", "dias_libres")
    op.drop_column("patios", "umbral_estancia_dias")
