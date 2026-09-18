from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.core.auditoria import registrar_auditoria
from app.db import get_db
from app.models.contenedor import Contenedor, Movimiento
from app.models.enums import EstadoContenedor, RolUsuario
from app.models.ubicacion import Ubicacion
from app.schemas.ubicacion import MovimientoCreate, MovimientoOut

router = APIRouter()

_ROLES_ESCRITURA = (RolUsuario.OPERADOR, RolUsuario.SUPERVISOR, RolUsuario.ADMIN)


@router.post("", response_model=MovimientoOut, status_code=status.HTTP_201_CREATED)
async def registrar_movimiento(
    payload: MovimientoCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Movimiento:
    ubicacion_result = await db.execute(
        select(Ubicacion).where(Ubicacion.id == payload.ubicacion_destino_id).with_for_update()
    )
    ubicacion = ubicacion_result.scalar_one_or_none()
    if ubicacion is None or not ubicacion.activo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ubicación no encontrada")

    ocupado_result = await db.execute(
        select(Contenedor.id).where(Contenedor.ubicacion_id == payload.ubicacion_destino_id)
    )
    if ocupado_result.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ubicación ya ocupada")

    contenedor_result = await db.execute(select(Contenedor).where(Contenedor.id == payload.contenedor_id))
    contenedor = contenedor_result.scalar_one_or_none()
    if contenedor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado")

    origen_id = contenedor.ubicacion_id
    contenedor.ubicacion_id = payload.ubicacion_destino_id
    contenedor.estado = EstadoContenedor.UBICADO

    movimiento = Movimiento(
        contenedor_id=contenedor.id,
        patio_id=contenedor.patio_id,
        tipo=payload.tipo,
        ubicacion_origen_id=origen_id,
        ubicacion_destino_id=payload.ubicacion_destino_id,
        operador_id=user.id,
        override_manual=payload.override_manual,
        motivo_override=payload.motivo_override,
        score_sugerido=payload.score_sugerido,
        score_elegido=payload.score_elegido,
    )
    db.add(movimiento)
    await db.flush()

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="mover",
        entidad="contenedores",
        entidad_id=str(contenedor.id),
        valor_anterior={"ubicacion_id": str(origen_id) if origen_id else None},
        valor_nuevo={"ubicacion_id": str(payload.ubicacion_destino_id)},
        patio_id=contenedor.patio_id,
    )
    await db.commit()
    return movimiento
