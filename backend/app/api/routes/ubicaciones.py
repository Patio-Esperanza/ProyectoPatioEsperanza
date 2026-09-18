from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.db import get_db
from app.models.contenedor import Contenedor
from app.models.enums import RolUsuario
from app.schemas.ubicacion import SugerenciaUbicacionRequest, SugerenciaUbicacionResponse
from app.services.ubicacion_algoritmo import sugerir_ubicacion

router = APIRouter()

_ROLES = (RolUsuario.OPERADOR, RolUsuario.SUPERVISOR, RolUsuario.ADMIN)


@router.post("/sugerir", response_model=SugerenciaUbicacionResponse)
async def sugerir(
    payload: SugerenciaUbicacionRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES)),
) -> SugerenciaUbicacionResponse:
    contenedor_result = await db.execute(select(Contenedor).where(Contenedor.id == payload.contenedor_id))
    contenedor = contenedor_result.scalar_one_or_none()
    if contenedor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado")

    try:
        candidato = await sugerir_ubicacion(
            db,
            patio_id=payload.patio_id,
            contenedor=contenedor,
            punto_referencia_ubicacion_id=payload.punto_referencia_ubicacion_id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))

    return SugerenciaUbicacionResponse(
        ubicacion_id=candidato.ubicacion_id, codigo=candidato.codigo, costo=candidato.costo
    )
