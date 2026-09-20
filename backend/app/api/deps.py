import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select, text
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

    current_user = CurrentUser(
        id=usuario.id,
        rol=RolUsuario(payload["rol"]),
        patios=[uuid.UUID(p) for p in payload.get("patios", [])],
        cliente_id=uuid.UUID(cliente_id_claim) if cliente_id_claim else None,
    )

    # Fija el contexto de RLS en cada request autenticado, siempre — nunca depender de
    # que el GUC quede "sin tocar". Una vez que Postgres crea el placeholder de una GUC
    # personalizada (aunque sea con SET LOCAL luego revertido), current_setting(..., true)
    # nunca vuelve a NULL en esa conexión del pool: queda en '' indefinidamente. Si algún
    # otro request ya la tocó antes, un request que no fije el GUC vería ese residuo, no
    # "sin restricción".
    await db.execute(
        text("SELECT set_config('app.rol', :rol, true)"), {"rol": current_user.rol.value}
    )
    await db.execute(
        text("SELECT set_config('app.patios_asignados', :patios, true)"),
        {"patios": ",".join(str(p) for p in current_user.patios)},
    )

    return current_user


def require_roles(*roles: RolUsuario):
    async def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.rol not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No autorizado para este recurso")
        return user

    return dependency
