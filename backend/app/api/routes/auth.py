from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import create_access_token, verify_password
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
