import datetime
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.core.auditoria import registrar_auditoria
from app.core.email import enviar_correo
from app.db import get_db
from app.models.contenedor import Contenedor
from app.models.enums import EstadoContenedor, RolUsuario
from app.models.ubicacion import Patio
from app.models.usuario import Usuario
from app.schemas.contenedor import (
    ContenedorCreate,
    ContenedorOut,
    ContenedorSolicitud,
    PinOut,
    PinVerificar,
    SolicitudSalida,
)

router = APIRouter()

_ROLES_ESCRITURA = (RolUsuario.OPERADOR, RolUsuario.SUPERVISOR, RolUsuario.ADMIN)


@router.get("", response_model=list[ContenedorOut])
async def listar_contenedores(
    estado: EstadoContenedor | None = Query(default=None),
    patio_id: uuid.UUID | None = Query(default=None),
    cliente_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> list[Contenedor]:
    query = select(Contenedor)

    if user.rol == RolUsuario.CLIENTE:
        query = query.where(Contenedor.cliente_id == user.cliente_id)
    else:
        if patio_id is not None:
            query = query.where(Contenedor.patio_id == patio_id)
        if cliente_id is not None:
            query = query.where(Contenedor.cliente_id == cliente_id)

    if estado is not None:
        query = query.where(Contenedor.estado == estado)

    if estado == EstadoContenedor.SOLICITUD_SALIDA:
        query = query.order_by(Contenedor.fecha_deseada_salida.asc())
    else:
        query = query.order_by(Contenedor.created_at.desc())

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=ContenedorOut, status_code=status.HTTP_201_CREATED)
async def crear_contenedor(
    payload: ContenedorCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Contenedor:
    contenedor = Contenedor(
        numero_contenedor=payload.numero_contenedor,
        tipo=payload.tipo,
        tamano=payload.tamano,
        patio_id=payload.patio_id,
        estado=EstadoContenedor.SOLICITUD_INGRESO,
        peso_kg=payload.peso_kg,
    )
    db.add(contenedor)
    await db.flush()

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="crear",
        entidad="contenedores",
        entidad_id=str(contenedor.id),
        valor_anterior=None,
        valor_nuevo={"numero_contenedor": contenedor.numero_contenedor, "estado": contenedor.estado.value},
        patio_id=contenedor.patio_id,
    )
    await db.commit()
    return contenedor


@router.post("/solicitar", response_model=ContenedorOut, status_code=status.HTTP_201_CREATED)
async def solicitar_contenedor(
    payload: ContenedorSolicitud,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.CLIENTE)),
) -> Contenedor:
    patio_result = await db.execute(
        select(Patio).where(Patio.activo.is_(True)).order_by(Patio.codigo).limit(1)
    )
    patio = patio_result.scalar_one_or_none()
    if patio is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No hay patios activos configurados")

    pin = f"{secrets.randbelow(10000):04d}"

    contenedor = Contenedor(
        numero_contenedor=payload.numero_contenedor,
        tipo=payload.tipo,
        tamano=payload.tamano,
        patio_id=patio.id,
        cliente_id=user.cliente_id,
        estado=EstadoContenedor.SOLICITUD_INGRESO,
        peso_kg=payload.peso_kg,
        fecha_estimada_salida=payload.fecha_estimada_retiro,
        pin_confirmacion=pin,
    )
    db.add(contenedor)
    await db.flush()

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="crear",
        entidad="contenedores",
        entidad_id=str(contenedor.id),
        valor_anterior=None,
        valor_nuevo={"numero_contenedor": contenedor.numero_contenedor, "estado": contenedor.estado.value},
        patio_id=contenedor.patio_id,
    )
    await db.commit()

    usuario_result = await db.execute(select(Usuario).where(Usuario.id == user.id))
    usuario = usuario_result.scalar_one()
    try:
        enviar_correo(
            usuario.email,
            "PIN de confirmación — Patio Esperanza",
            f"<p>Tu PIN de confirmación es <strong>{pin}</strong>. "
            f"Preséntalo al operador en la entrada del patio.</p>",
        )
    except Exception as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "No se pudo enviar el correo con tu PIN, consúltalo después o contacta al administrador",
        ) from exc

    return contenedor


@router.post("/verificar-pin", response_model=ContenedorOut)
async def verificar_pin(
    payload: PinVerificar,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Contenedor:
    result = await db.execute(
        select(Contenedor).where(Contenedor.numero_contenedor == payload.numero_contenedor)
    )
    contenedor = result.scalar_one_or_none()
    if contenedor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado")

    if contenedor.estado != EstadoContenedor.SOLICITUD_INGRESO:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Este contenedor no está pendiente de verificación de PIN"
        )

    if contenedor.pin_confirmacion != payload.pin:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "PIN incorrecto")

    contenedor.estado = EstadoContenedor.EN_PORTERIA
    contenedor.pin_verificado_en = func.now()
    contenedor.pin_verificado_por = user.id

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="verificar_pin",
        entidad="contenedores",
        entidad_id=str(contenedor.id),
        valor_anterior={"estado": EstadoContenedor.SOLICITUD_INGRESO.value},
        valor_nuevo={"estado": contenedor.estado.value},
        patio_id=contenedor.patio_id,
    )
    await db.commit()
    await db.refresh(contenedor)
    return contenedor


@router.post("/{contenedor_id}/solicitar-salida", response_model=ContenedorOut)
async def solicitar_salida(
    contenedor_id: str,
    payload: SolicitudSalida,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.CLIENTE)),
) -> Contenedor:
    result = await db.execute(select(Contenedor).where(Contenedor.id == contenedor_id))
    contenedor = result.scalar_one_or_none()
    if contenedor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado")

    if contenedor.cliente_id != user.cliente_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "No autorizado para solicitar la salida de este contenedor"
        )

    if contenedor.estado != EstadoContenedor.UBICADO:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Este contenedor no está disponible para solicitar salida"
        )

    patio_result = await db.execute(select(Patio).where(Patio.id == contenedor.patio_id))
    patio = patio_result.scalar_one()

    fecha_deseada = payload.fecha_deseada_salida
    if fecha_deseada.tzinfo is None:
        fecha_deseada = fecha_deseada.replace(tzinfo=datetime.timezone.utc)
    minimo = datetime.timedelta(hours=patio.anticipacion_minima_horas)
    ahora = datetime.datetime.now(datetime.timezone.utc)
    if fecha_deseada < ahora + minimo:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"La fecha de salida debe ser al menos {patio.anticipacion_minima_horas} horas "
            "después de ahora para este patio",
        )

    contenedor.estado = EstadoContenedor.SOLICITUD_SALIDA
    contenedor.fecha_deseada_salida = fecha_deseada
    contenedor.salida_solicitada_en = func.now()

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="solicitar_salida",
        entidad="contenedores",
        entidad_id=str(contenedor.id),
        valor_anterior={"estado": EstadoContenedor.UBICADO.value},
        valor_nuevo={"estado": contenedor.estado.value},
        patio_id=contenedor.patio_id,
    )
    await db.commit()
    await db.refresh(contenedor)
    return contenedor


@router.get("/{contenedor_id}/pin", response_model=PinOut)
async def obtener_pin(
    contenedor_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> Contenedor:
    result = await db.execute(select(Contenedor).where(Contenedor.id == contenedor_id))
    contenedor = result.scalar_one_or_none()
    if contenedor is None or contenedor.pin_confirmacion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Este contenedor no tiene PIN asociado")

    es_dueno = user.rol == RolUsuario.CLIENTE and contenedor.cliente_id == user.cliente_id
    if user.rol != RolUsuario.ADMIN and not es_dueno:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No autorizado para ver este PIN")

    return contenedor


@router.get("/{contenedor_id}", response_model=ContenedorOut)
async def obtener_contenedor(
    contenedor_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> Contenedor:
    result = await db.execute(select(Contenedor).where(Contenedor.id == contenedor_id))
    contenedor = result.scalar_one_or_none()
    if contenedor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado")
    return contenedor
