from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.db import get_db
from app.models.contenedor import Contenedor
from app.models.enums import RolUsuario
from app.models.ubicacion import Carril, Tira, Tramo, Ubicacion
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
    if payload.contenedor_id is not None:
        contenedor_result = await db.execute(
            select(Contenedor).where(
                Contenedor.id == payload.contenedor_id,
                Contenedor.patio_id == payload.patio_id,
            )
        )
        contenedor = contenedor_result.scalar_one_or_none()
        if contenedor is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado en este patio")
    else:
        contenedor_result = await db.execute(
            select(Contenedor).where(
                Contenedor.patio_id == payload.patio_id,
                Contenedor.numero_contenedor == payload.numero_contenedor,
            )
        )
        contenedores = contenedor_result.scalars().all()
        if not contenedores:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado en este patio")
        if len(contenedores) > 1:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Hay mas de un contenedor con ese numero en este patio"
            )
        contenedor = contenedores[0]

    if payload.punto_referencia_ubicacion_id is not None:
        punto_referencia_id = payload.punto_referencia_ubicacion_id
    else:
        referencia_result = await db.execute(
            select(Ubicacion)
            .join(Tira, Tira.id == Ubicacion.tira_id)
            .join(Tramo, Tramo.id == Tira.tramo_id)
            .join(Carril, Carril.id == Tramo.carril_id)
            .where(Carril.patio_id == payload.patio_id, Ubicacion.codigo == payload.punto_referencia_codigo)
        )
        punto_referencia = referencia_result.scalars().first()
        if punto_referencia is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "Ubicacion de referencia no encontrada en este patio"
            )
        punto_referencia_id = punto_referencia.id

    try:
        candidato = await sugerir_ubicacion(
            db,
            patio_id=payload.patio_id,
            contenedor=contenedor,
            punto_referencia_ubicacion_id=punto_referencia_id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))

    return SugerenciaUbicacionResponse(
        ubicacion_id=candidato.ubicacion_id,
        codigo=candidato.codigo,
        costo=candidato.costo,
        tira_id=candidato.tira_id,
        nivel=candidato.nivel,
    )
