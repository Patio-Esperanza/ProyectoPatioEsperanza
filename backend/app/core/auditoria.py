import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auditoria import Auditoria


async def registrar_auditoria(
    db: AsyncSession,
    *,
    usuario_id: uuid.UUID | None,
    rol: str,
    ip: str,
    dispositivo: str,
    accion: str,
    entidad: str,
    entidad_id: str,
    valor_anterior: dict[str, Any] | None,
    valor_nuevo: dict[str, Any] | None,
    patio_id: uuid.UUID | None,
) -> None:
    db.add(
        Auditoria(
            usuario_id=usuario_id,
            rol=rol,
            ip=ip,
            dispositivo=dispositivo,
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
            valor_anterior=valor_anterior,
            valor_nuevo=valor_nuevo,
            patio_id=patio_id,
        )
    )
