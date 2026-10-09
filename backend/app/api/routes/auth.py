import math
import uuid
from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import create_access_token, decode_token_allow_expired, verify_password
from app.db import get_db
from app.models.usuario import Usuario, UsuarioPatio
from app.schemas.auth import TokenResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    result = await db.execute(
        select(Usuario).where(Usuario.email == form.username, Usuario.activo.is_(True))
    )
    usuario = result.scalar_one_or_none()
    if (
        usuario is None
        or usuario.password_hash is None
        or not verify_password(form.password, usuario.password_hash)
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")

    patios_result = await db.execute(
        select(UsuarioPatio.patio_id).where(UsuarioPatio.usuario_id == usuario.id)
    )
    patios = [str(row[0]) for row in patios_result.all()]

    token = create_access_token(
        str(usuario.id),
        usuario.tipo.value,
        patios,
        settings.jwt_expires_minutes,
        cliente_id=str(usuario.cliente_id) if usuario.cliente_id else None,
    )
    return TokenResponse(access_token=token)


def _no_autorizado() -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Token inválido o caducado",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Un token ya vencido sigue sirviendo para renovar durante esta ventana: el usuario que
# vuelve a la pestaña después de un rato no debe perder lo que estaba capturando. Sin el
# límite el token sería eterno, así que la ventana es corta a propósito.
_GRACIA_REFRESH_SEGUNDOS = 300


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    authorization: str | None = Header(default=None), db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    try:
        scheme, token = (authorization or "").split()
        if scheme.lower() != "bearer":
            raise ValueError("Esquema inválido")
        payload = decode_token_allow_expired(token)
        exp = payload.get("exp")
        sub = payload.get("sub")
        if (
            not isinstance(exp, (int, float))
            or isinstance(exp, bool)
            or not math.isfinite(exp)
            or exp < datetime.now(timezone.utc).timestamp() - _GRACIA_REFRESH_SEGUNDOS
            or not isinstance(sub, str)
        ):
            raise ValueError("Claims inválidos o token caducado")
        usuario_id = uuid.UUID(sub)
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise _no_autorizado() from None

    # El rol, los patios y el estado se releen de la base, nunca se copian del token
    # viejo: desactivar a alguien o cambiarle los patios tiene que surtir efecto en la
    # siguiente renovación. Los patios alimentan RLS, así que un valor rancio aquí
    # equivale a dar acceso a un patio que ya no le toca.
    result = await db.execute(
        select(Usuario).where(Usuario.id == usuario_id, Usuario.activo.is_(True))
    )
    usuario = result.scalar_one_or_none()
    if usuario is None:
        raise _no_autorizado()

    patios_result = await db.execute(
        select(UsuarioPatio.patio_id).where(UsuarioPatio.usuario_id == usuario.id)
    )
    patios = [str(row[0]) for row in patios_result.all()]

    return TokenResponse(
        access_token=create_access_token(
            str(usuario.id),
            usuario.tipo.value,
            patios,
            settings.jwt_expires_minutes,
            cliente_id=str(usuario.cliente_id) if usuario.cliente_id else None,
        )
    )
