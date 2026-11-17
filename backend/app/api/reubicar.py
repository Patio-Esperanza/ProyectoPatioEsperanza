import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, require_roles
from app.core.auditoria import registrar_auditoria
from app.db import get_db
from app.models.contenedor import Contenedor, Movimiento
from app.models.enums import EstadoContenedor, RolUsuario, TipoMovimiento
from app.models.tira import Tira
from app.models.ubicacion import Ubicacion
from app.schemas.ubicacion_grua import UbicacionUbicarResponse

router = APIRouter()

_ROLES_GRUA = (RolUsuario.OPERADOR_GRUA, RolUsuario.OPERADOR, RolUsuario.SUPERVISOR, RolUsuario.ADMIN)


class ContenedorReubicarCreate(BaseModel):
    ubicacion_destino_id: uuid.UUID
    motivo: str = Field(min_length=1)


@router.post("/contenedores/{contenedor_id}/reubicar", response_model=UbicacionUbicarResponse)
async def reubicar_contenedor(
    contenedor_id: str,
    payload: ContenedorReubicarCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_GRUA)),
) -> UbicacionUbicarResponse:
    # 1. Fetch target location
    ubicacion_result = await db.execute(
        select(Ubicacion, Tira)
        .join(Tira, Ubicacion.tira_id == Tira.id)
        .where(Ubicacion.id == payload.ubicacion_destino_id)
        .with_for_update()
    )
    row = ubicacion_result.first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ubicación de destino no encontrada")
    destino, tira = row
    if not destino.activo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ubicación de destino inactiva")

    # 2. Check max levels
    if destino.nivel > tira.max_niveles:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"El nivel {destino.nivel} excede el máximo permitido ({tira.max_niveles}) para esta tira",
        )

    # 3. Check floating position (if nivel > 1, nivel-1 must be occupied)
    if destino.nivel > 1:
        inf_result = await db.execute(
            select(Ubicacion.id)
            .where(
                Ubicacion.tira_id == destino.tira_id,
                Ubicacion.nivel == destino.nivel - 1,
            )
        )
        ubicacion_inf_id = inf_result.scalar_one_or_none()
        if ubicacion_inf_id is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Ubicación inferior no existe")

        ocupado_inf_result = await db.execute(
            select(Contenedor.id).where(Contenedor.ubicacion_id == ubicacion_inf_id)
        )
        if ocupado_inf_result.scalar_one_or_none() is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Posición flotante: el nivel inferior debe estar ocupado",
            )

    # 4. Check target location is not occupied
    ocupado_result = await db.execute(
        select(Contenedor.id).where(Contenedor.ubicacion_id == payload.ubicacion_destino_id)
    )
    if ocupado_result.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "La ubicación de destino ya está ocupada")

    # 5. Fetch container
    try:
        cont_uuid = uuid.UUID(contenedor_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ID de contenedor inválido")

    contenedor_result = await db.execute(
        select(Contenedor).where(Contenedor.id == cont_uuid).with_for_update()
    )
    contenedor = contenedor_result.scalar_one_or_none()
    if contenedor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado")

    # 6. Check unstacking violation (no sacar de abajo): if container is currently located, check if any container is on top in the same tira
    if contenedor.ubicacion_id is not None:
        curr_ubicacion_result = await db.execute(
            select(Ubicacion).where(Ubicacion.id == contenedor.ubicacion_id)
        )
        curr_ubicacion = curr_ubicacion_result.scalar_one_or_none()
        if curr_ubicacion is not None:
            # Find active containers in same tira with strictly higher level
            encima_result = await db.execute(
                select(Contenedor.numero_contenedor, Ubicacion.nivel)
                .join(Ubicacion, Contenedor.ubicacion_id == Ubicacion.id)
                .where(
                    Ubicacion.tira_id == curr_ubicacion.tira_id,
                    Ubicacion.nivel > curr_ubicacion.nivel,
                    Contenedor.estado != EstadoContenedor.DESPACHADO,
                    Contenedor.estado != EstadoContenedor.RECHAZADO,
                )
            )
            contenedores_encima = [row[0] for row in encima_result.all()]
            if contenedores_encima:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"No se puede reubicar: hay contenedores encima que deben moverse primero: {', '.join(contenedores_encima)}",
                )

    # 7. Execute relocation
    origen_id = contenedor.ubicacion_id
    contenedor.ubicacion_id = payload.ubicacion_destino_id
    contenedor.estado = EstadoContenedor.UBICADO

    movimiento = Movimiento(
        contenedor_id=contenedor.id,
        patio_id=contenedor.patio_id,
        tipo=TipoMovimiento.REUBICACION,
        ubicacion_origen_id=origen_id,
        ubicacion_destino_id=payload.ubicacion_destino_id,
        operador_id=user.id,
        override_manual=False,
        motivo_override=payload.motivo,
    )
    db.add(movimiento)
    await db.flush()

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="reubicar",
        entidad="contenedores",
        entidad_id=str(contenedor.id),
        valor_anterior={"ubicacion_id": str(origen_id) if origen_id else None},
        valor_nuevo={"ubicacion_id": str(payload.ubicacion_destino_id), "motivo": payload.motivo},
        patio_id=contenedor.patio_id,
    )
    await db.commit()
    await db.refresh(contenedor)

    return UbicacionUbicarResponse(contenedor=contenedor)
