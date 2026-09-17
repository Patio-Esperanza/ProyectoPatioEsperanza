import os

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.auditoria import registrar_auditoria
from app.models.auditoria import Auditoria
from app.models.enums import RolUsuario
from app.models.usuario import Usuario


@pytest.mark.anyio
async def test_registrar_auditoria_inserta_fila(db_session):
    usuario = Usuario(tipo=RolUsuario.ADMIN, email="audit@patio.mx", password_hash="h", activo=True)
    db_session.add(usuario)
    await db_session.flush()

    await registrar_auditoria(
        db_session,
        usuario_id=usuario.id,
        rol=RolUsuario.ADMIN.value,
        ip="127.0.0.1",
        dispositivo="pytest",
        accion="crear",
        entidad="usuarios",
        entidad_id=str(usuario.id),
        valor_anterior=None,
        valor_nuevo={"email": usuario.email},
        patio_id=None,
    )
    await db_session.flush()

    result = await db_session.execute(text("SELECT accion, entidad FROM auditoria"))
    row = result.one()
    assert row.accion == "crear"
    assert row.entidad == "usuarios"


@pytest.mark.anyio
async def test_rol_app_no_puede_update_ni_delete_auditoria(db_session):
    await db_session.execute(
        text(
            "INSERT INTO auditoria (id, ts, usuario_id, rol, ip, dispositivo, accion, entidad, entidad_id, "
            "valor_anterior, valor_nuevo, patio_id) VALUES "
            "(gen_random_uuid(), now(), NULL, 'admin', '127.0.0.1', 'pytest', 'crear', 'x', 'x', NULL, NULL, NULL)"
        )
    )
    await db_session.flush()

    app_engine = create_async_engine(os.environ["DATABASE_URL"])
    async with app_engine.connect() as conn:
        with pytest.raises(DBAPIError, match="permission denied"):
            await conn.execute(text("UPDATE auditoria SET accion = 'modificado'"))
    await app_engine.dispose()
