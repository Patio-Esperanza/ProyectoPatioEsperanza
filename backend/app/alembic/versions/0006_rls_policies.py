"""rls policies por patio_id

Revision ID: 0006_rls_policies
Revises: 0005_contenedor_movimiento
Create Date: 2026-09-14
"""
from alembic import op

revision = "0006_rls_policies"
down_revision = "0005_contenedor_movimiento"
branch_labels = None
depends_on = None

_TABLAS = ("contenedores", "movimientos", "auditoria")


def upgrade() -> None:
    for tabla in _TABLAS:
        op.execute(f"ALTER TABLE {tabla} ENABLE ROW LEVEL SECURITY;")
        op.execute(
            f"""
            CREATE POLICY {tabla}_por_patio ON {tabla}
              USING (
                current_setting('app.rol', true) IS NULL
                OR current_setting('app.rol', true) = 'admin'
                OR patio_id::text = ANY(
                  string_to_array(coalesce(current_setting('app.patios_asignados', true), ''), ',')
                )
              )
              WITH CHECK (true);
            """
        )


def downgrade() -> None:
    for tabla in _TABLAS:
        op.execute(f"DROP POLICY IF EXISTS {tabla}_por_patio ON {tabla};")
        op.execute(f"ALTER TABLE {tabla} DISABLE ROW LEVEL SECURITY;")
