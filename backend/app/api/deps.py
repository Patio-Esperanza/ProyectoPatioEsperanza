import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db import get_db
from app.models.enums import RolUsuario
from app.models.usuario import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@dataclass
class CurrentUser:
    id: uuid.UUID
    rol: RolUsuario
    patios: list[uuid.UUID]
    cliente_id: uuid.UUID | None


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> CurrentUser:
    try:
        payload = decode_access_token(token)
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")

    usuario_id = uuid.UUID(payload["sub"])
    result = await db.execute(
        select(Usuario).where(Usuario.id == usuario_id, Usuario.activo.is_(True))
    )
    usuario = result.scalar_one_or_none()
    if usuario is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no encontrado")

    cliente_id_claim = payload.get("cliente_id")

    return CurrentUser(
        id=usuario.id,
        rol=RolUsuario(payload["rol"]),
        patios=[uuid.UUID(p) for p in payload.get("patios", [])],
        cliente_id=uuid.UUID(cliente_id_claim) if cliente_id_claim else None,
    )


def require_roles(*roles: RolUsuario):
    async def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.rol not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No autorizado para este recurso")
        return user

    return dependency


from sqlalchemy import text


async def get_scoped_db(
    user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AsyncSession:
    await db.execute(text("SELECT set_config('app.rol', :rol, true)"), {"rol": user.rol.value})
    await db.execute(
        text("SELECT set_config('app.patios_asignados', :patios, true)"),
        {"patios": ",".join(str(p) for p in user.patios)},
    )
    return db
