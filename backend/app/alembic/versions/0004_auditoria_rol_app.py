"""auditoria + rol patio_app restringido

Revision ID: 0004_auditoria_rol_app
Revises: 0003_cliente_usuario
Create Date: 2026-09-14
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_auditoria_rol_app"
down_revision = "0003_cliente_usuario"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auditoria",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rol", sa.String(30), nullable=False),
        sa.Column("ip", sa.String(45), nullable=False),
        sa.Column("dispositivo", sa.String(200), nullable=False),
        sa.Column("accion", sa.String(50), nullable=False),
        sa.Column("entidad", sa.String(50), nullable=False),
        sa.Column("entidad_id", sa.String(50), nullable=False),
        sa.Column("valor_anterior", postgresql.JSONB(), nullable=True),
        sa.Column("valor_nuevo", postgresql.JSONB(), nullable=True),
        sa.Column("patio_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_auditoria_entidad", "auditoria", ["entidad", "entidad_id"])

    op.execute(
        """
        DO $$ BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'patio_app') THEN
            CREATE ROLE patio_app LOGIN PASSWORD 'patio_app';
          END IF;
        END $$;
        """
    )
    op.execute("GRANT CONNECT ON DATABASE " + op.get_bind().engine.url.database + " TO patio_app;")
    op.execute("GRANT USAGE ON SCHEMA public TO patio_app;")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO patio_app;")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO patio_app;")
    op.execute("REVOKE UPDATE, DELETE ON auditoria FROM patio_app;")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO patio_app;"
    )


def downgrade() -> None:
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM patio_app;")
    op.drop_index("ix_auditoria_entidad", table_name="auditoria")
    op.drop_table("auditoria")
