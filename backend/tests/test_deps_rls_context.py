import uuid

import pytest
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.db import engine
from app.models.enums import RolUsuario
from app.models.usuario import Usuario


@pytest.mark.anyio
async def test_get_current_user_no_hereda_rol_de_una_conexion_reutilizada():
    admin_id = uuid.uuid4()
    operador_id = uuid.uuid4()

    conn = await engine.connect()
    try:
        setup = AsyncSession(bind=conn, expire_on_commit=False)
        setup.add_all(
            [
                Usuario(
                    id=admin_id,
                    tipo=RolUsuario.ADMIN,
                    email=f"{admin_id}@rls-test.mx",
                    password_hash="hash",
                    activo=True,
                ),
                Usuario(
                    id=operador_id,
                    tipo=RolUsuario.OPERADOR,
                    email=f"{operador_id}@rls-test.mx",
                    password_hash="hash",
                    activo=True,
                ),
            ]
        )
        await setup.commit()
        await setup.close()

        token_admin = create_access_token(str(admin_id), "admin", [], 60)
        session_a = AsyncSession(bind=conn, expire_on_commit=False)
        await get_current_user(token=token_admin, db=session_a)
        rol_a = (
            await session_a.execute(text("SELECT current_setting('app.rol', true)"))
        ).scalar()
        assert rol_a == "admin"
        await session_a.close()

        token_operador = create_access_token(str(operador_id), "operador", [], 60)
        session_b = AsyncSession(bind=conn, expire_on_commit=False)
        await get_current_user(token=token_operador, db=session_b)
        rol_b = (
            await session_b.execute(text("SELECT current_setting('app.rol', true)"))
        ).scalar()
        assert rol_b == "operador"
        await session_b.close()

        cleanup = AsyncSession(bind=conn, expire_on_commit=False)
        await cleanup.execute(delete(Usuario).where(Usuario.id.in_([admin_id, operador_id])))
        await cleanup.commit()
        await cleanup.close()
    finally:
        await conn.close()
