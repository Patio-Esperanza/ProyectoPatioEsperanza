import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.db import get_db
from app.models.socio import CredencialSocio


@dataclass
class CurrentSocio:
    id: uuid.UUID
    nombre: str
    cliente_id: uuid.UUID | None
    patios_permitidos: list[uuid.UUID]
    webhook_url: str | None
    webhook_secreto: str | None


async def verificar_api_key(
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> CurrentSocio:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Encabezado Authorization requerido",
        )

    auth_header = authorization.strip()
    if not auth_header.startswith("ApiKey "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Esquema de autenticación inválido. Use 'ApiKey <prefijo>.<secreto>'",
        )

    token = auth_header[7:].strip()
    if "." not in token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato de API Key inválido. Use <prefijo>.<secreto>",
        )

    prefijo, secreto = token.split(".", 1)

    result = await db.execute(
        select(CredencialSocio).where(
            CredencialSocio.prefijo == prefijo, CredencialSocio.activo.is_(True)
        )
    )
    credencial = result.scalar_one_or_none()

    if credencial is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credencial socio no encontrada o inactiva",
        )

    if not verify_password(secreto, credencial.secreto_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida",
        )

    credencial.ultimo_uso_en = datetime.now(timezone.utc)
    await db.flush()

    await db.execute(text("SELECT set_config('app.rol', 'socio', true)"))
    await db.execute(
        text("SELECT set_config('app.patios_asignados', :patios, true)"),
        {"patios": ",".join(str(p) for p in credencial.patios_permitidos)},
    )

    return CurrentSocio(
        id=credencial.id,
        nombre=credencial.nombre,
        cliente_id=credencial.cliente_id,
        patios_permitidos=credencial.patios_permitidos,
        webhook_url=credencial.webhook_url,
        webhook_secreto=credencial.webhook_secreto,
    )
