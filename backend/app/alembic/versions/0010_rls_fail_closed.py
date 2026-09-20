"""rls: agregar bypass explicito para cliente (ya no depende de que el GUC quede sin tocar)

Revision ID: 0010_rls_fail_closed
Revises: 0009_solicitud_salida
Create Date: 2026-09-20
"""
from alembic import op

revision = "0010_rls_fail_closed"
down_revision = "0009_solicitud_salida"
branch_labels = None
depends_on = None

_TABLAS = ("contenedores", "movimientos", "auditoria")


def upgrade() -> None:
    for tabla in _TABLAS:
        op.execute(
            f"""
            ALTER POLICY {tabla}_por_patio ON {tabla}
              USING (
                current_setting('app.rol', true) IS NULL
                OR current_setting('app.rol', true) = 'admin'
                OR current_setting('app.rol', true) = 'cliente'
                OR patio_id::text = ANY(
                  string_to_array(coalesce(current_setting('app.patios_asignados', true), ''), ',')
                )
              );
            """
        )


def downgrade() -> None:
    for tabla in _TABLAS:
        op.execute(
            f"""
            ALTER POLICY {tabla}_por_patio ON {tabla}
              USING (
                current_setting('app.rol', true) IS NULL
                OR current_setting('app.rol', true) = 'admin'
                OR patio_id::text = ANY(
                  string_to_array(coalesce(current_setting('app.patios_asignados', true), ''), ',')
                )
              );
            """
        )
