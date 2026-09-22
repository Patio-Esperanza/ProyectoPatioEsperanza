import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.db import get_db
from app.models.enums import RolUsuario
from app.schemas.mapa import DetalleTiraOut
from app.services.mapa_patio import obtener_detalle_tira

router = APIRouter()

_ROLES = (RolUsuario.OPERADOR, RolUsuario.SUPERVISOR, RolUsuario.ADMIN)


@router.get("/{tira_id}", response_model=DetalleTiraOut)
async def detalle_tira(
    tira_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES)),
) -> DetalleTiraOut:
    detalle = await obtener_detalle_tira(db, tira_id)
    if detalle is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tira no encontrada")
    return detalle
