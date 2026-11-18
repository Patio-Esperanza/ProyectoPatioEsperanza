import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.api.deps import CurrentUser, require_roles
from app.core.auditoria import registrar_auditoria
from app.core.security import verify_password
from app.db import get_db
from app.models.contenedor import Contenedor, Movimiento
from app.models.enums import EstadoContenedor, RolUsuario, TipoMovimiento
from app.models.servicio import EstadoServicio, ServicioCatalogo, ServicioContenedor
from app.schemas.contenedor import ContenedorOut
from app.schemas.salidas import (
    SalidaDespacharCreate,
    SalidaDespacharResponse,
    SalidaListoCreate,
    SalidaListoResponse,
)

router = APIRouter()

_ROLES_DESPACHO = (RolUsuario.DESPACHADOR, RolUsuario.GUARDIA, RolUsuario.SUPERVISOR, RolUsuario.ADMIN)


@router.post("/contenedores/{contenedor_id}/despachar", response_model=SalidaDespacharResponse)
async def despachar_contenedor(
    contenedor_id: str,
    payload: SalidaDespacharCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_DESPACHO)),
) -> SalidaDespacharResponse:
    if user.rol == RolUsuario.GUARDIA and not user.patios:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Guardia sin patios asignados")

    result = await db.execute(
        select(Contenedor).where(Contenedor.id == contenedor_id).with_for_update()
    )
    contenedor = result.scalar_one_or_none()
    if contenedor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado")

    if user.rol == RolUsuario.GUARDIA and contenedor.patio_id not in user.patios:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "El contenedor no pertenece al patio del usuario")

    if contenedor.estado != EstadoContenedor.EN_PORTERIA_SALIDA:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El contenedor no está listo en portería para salida",
        )

    # Check if there are any active service orders that block exit
    servicios_pendientes = await db.execute(
        select(ServicioContenedor)
        .join(ServicioCatalogo, ServicioContenedor.servicio_catalogo_id == ServicioCatalogo.id)
        .where(
            ServicioContenedor.contenedor_id == contenedor.id,
            ServicioCatalogo.bloquea_salida.is_(True),
            ServicioContenedor.estado.in_([EstadoServicio.SOLICITADO, EstadoServicio.PROGRAMADO, EstadoServicio.EN_PROCESO])
        )
    )
    servicio_bloqueante = servicios_pendientes.scalars().first()
    if servicio_bloqueante is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El contenedor tiene servicios pendientes que bloquean la salida"
        )

    if contenedor.pin_salida_hash:
        if not verify_password(payload.pin_salida, contenedor.pin_salida_hash):
            contenedor.pin_salida_intentos += 1
            await db.commit()
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "PIN de salida incorrecto")

    origen_id = contenedor.ubicacion_id
    contenedor.estado = EstadoContenedor.DESPACHADO
    contenedor.ubicacion_id = None
    contenedor.fecha_salida = func.now()

    movimiento = Movimiento(
        contenedor_id=contenedor.id,
        patio_id=contenedor.patio_id,
        tipo=TipoMovimiento.SALIDA,
        ubicacion_origen_id=origen_id,
        ubicacion_destino_id=None,
        operador_id=user.id,
    )
    db.add(movimiento)
    await db.flush()

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="despachar",
        entidad="contenedores",
        entidad_id=str(contenedor.id),
        valor_anterior={"estado": EstadoContenedor.EN_PORTERIA_SALIDA.value},
        valor_nuevo={"estado": contenedor.estado.value},
        patio_id=contenedor.patio_id,
    )
    await db.commit()
    await db.refresh(contenedor)

    return SalidaDespacharResponse(contenedor=contenedor)


@router.post("/contenedores/{contenedor_id}/listo", response_model=SalidaListoResponse)
async def marcar_listo_puerta(
    contenedor_id: str,
    payload: SalidaListoCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_DESPACHO)),
) -> SalidaListoResponse:
    result = await db.execute(
        select(Contenedor).where(Contenedor.id == contenedor_id).with_for_update()
    )
    contenedor = result.scalar_one_or_none()
    if contenedor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado")

    if contenedor.estado not in (EstadoContenedor.SOLICITUD_SALIDA, EstadoContenedor.UBICADO):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El contenedor no está en solicitud de salida o ubicado",
        )

    estado_anterior = contenedor.estado.value
    contenedor.estado = EstadoContenedor.EN_PORTERIA_SALIDA

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="marcar_listo",
        entidad="contenedores",
        entidad_id=str(contenedor.id),
        valor_anterior={"estado": estado_anterior},
        valor_nuevo={"estado": contenedor.estado.value},
        patio_id=contenedor.patio_id,
    )
    await db.commit()
    await db.refresh(contenedor)

    return SalidaListoResponse(contenedor=contenedor)
