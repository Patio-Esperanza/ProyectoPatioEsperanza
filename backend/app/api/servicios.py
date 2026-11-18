import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.api.deps import CurrentUser, require_roles
from app.core.auditoria import registrar_auditoria
from app.db import get_db
from app.models.contenedor import Contenedor
from app.models.enums import EstadoContenedor, RolUsuario
from app.models.evidencia import Evidencia
from app.models.servicio import EstadoServicio, ServicioCatalogo, ServicioContenedor
from app.schemas.servicio import (
    ServicioCatalogoCreate,
    ServicioCatalogoOut,
    ServicioCatalogoUpdate,
    ServicioContenedorCreate,
    ServicioContenedorMotivo,
    ServicioContenedorOut,
    ServicioContenedorProgramar,
    ServicioContenedorTerminar,
)

router = APIRouter()

_ROLES_INTERNOS = (RolUsuario.CUADRILLA, RolUsuario.SUPERVISOR, RolUsuario.ADMIN, RolUsuario.OPERADOR)
_ROLES_GESTION_ORDEN = (RolUsuario.CUADRILLA, RolUsuario.SUPERVISOR, RolUsuario.ADMIN)
_ROLES_PROGRAMAR = (RolUsuario.SUPERVISOR, RolUsuario.ADMIN)


@router.get("/servicios/catalogo", response_model=list[ServicioCatalogoOut])
async def listar_catalogo_servicios(
    patio_id: uuid.UUID | None = Query(default=None),
    cliente_solicitar: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.CLIENTE, RolUsuario.OPERADOR, RolUsuario.SUPERVISOR, RolUsuario.ADMIN, RolUsuario.CUADRILLA)),
) -> list[ServicioCatalogo]:
    query = select(ServicioCatalogo).where(ServicioCatalogo.activo.is_(True))
    if patio_id is not None:
        query = query.where((ServicioCatalogo.patio_id == patio_id) | (ServicioCatalogo.patio_id.is_(None)))
    if user.rol == RolUsuario.CLIENTE or cliente_solicitar:
        query = query.where(ServicioCatalogo.cliente_puede_solicitar.is_(True))

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/servicios/catalogo", response_model=ServicioCatalogoOut, status_code=status.HTTP_201_CREATED)
async def crear_catalogo_servicio(
    payload: ServicioCatalogoCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.ADMIN)),
) -> ServicioCatalogo:
    servicio = ServicioCatalogo(**payload.model_dump())
    db.add(servicio)
    await db.flush()

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="crear_catalogo",
        entidad="servicios_catalogo",
        entidad_id=str(servicio.id),
        valor_nuevo=payload.model_dump(mode="json"),
        patio_id=payload.patio_id,
    )
    await db.commit()
    await db.refresh(servicio)
    return servicio


@router.patch("/servicios/catalogo/{catalogo_id}", response_model=ServicioCatalogoOut)
async def actualizar_catalogo_servicio(
    catalogo_id: uuid.UUID,
    payload: ServicioCatalogoUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.ADMIN)),
) -> ServicioCatalogo:
    result = await db.execute(select(ServicioCatalogo).where(ServicioCatalogo.id == catalogo_id))
    servicio = result.scalar_one_or_none()
    if servicio is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Servicio de catálogo no encontrado")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(servicio, key, value)

    await db.flush()
    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="actualizar_catalogo",
        entidad="servicios_catalogo",
        entidad_id=str(servicio.id),
        valor_nuevo=update_data,
        patio_id=servicio.patio_id,
    )
    await db.commit()
    await db.refresh(servicio)
    return servicio


@router.post("/contenedores/{contenedor_id}/servicios", response_model=ServicioContenedorOut, status_code=status.HTTP_201_CREATED)
async def solicitar_servicio_contenedor(
    contenedor_id: uuid.UUID,
    payload: ServicioContenedorCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.CLIENTE, RolUsuario.SUPERVISOR, RolUsuario.ADMIN, RolUsuario.OPERADOR)),
) -> ServicioContenedor:
    # 1. Verify container exists
    cont_res = await db.execute(select(Contenedor).where(Contenedor.id == contenedor_id))
    contenedor = cont_res.scalar_one_or_none()
    if contenedor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado")

    if user.rol == RolUsuario.CLIENTE:
        if contenedor.cliente_id != user.cliente_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado o sin acceso")

    # 2. Verify catalog service exists and is active
    cat_res = await db.execute(select(ServicioCatalogo).where(ServicioCatalogo.id == payload.servicio_catalogo_id))
    catalogo = cat_res.scalar_one_or_none()
    if catalogo is None or not catalogo.activo:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Servicio de catálogo no válido o inactivo")

    if user.rol == RolUsuario.CLIENTE and not catalogo.cliente_puede_solicitar:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "El cliente no puede solicitar este servicio")

    # 3. Validate required related unit (e.g. Traspaleo)
    if catalogo.requiere_unidad_relacionada:
        if not payload.unidad_relacionada_tipo or (not payload.contenedor_relacionado_id and not payload.unidad_relacionada_ref):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Este servicio requiere especificar una unidad relacionada (tipo y referencia/contenedor)")

    # 4. Create service order
    servicio = ServicioContenedor(
        contenedor_id=contenedor.id,
        servicio_catalogo_id=catalogo.id,
        cliente_id=contenedor.cliente_id or user.cliente_id,
        estado=EstadoServicio.SOLICITADO,
        solicitado_por=user.id,
        notas=payload.notas,
        unidad_relacionada_tipo=payload.unidad_relacionada_tipo,
        contenedor_relacionado_id=payload.contenedor_relacionado_id,
        unidad_relacionada_ref=payload.unidad_relacionada_ref,
    )
    db.add(servicio)
    await db.flush()

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="solicitar_servicio",
        entidad="servicios_contenedor",
        entidad_id=str(servicio.id),
        valor_nuevo={"estado": servicio.estado.value, "servicio_catalogo_id": str(catalogo.id)},
        patio_id=contenedor.patio_id,
    )
    await db.commit()
    await db.refresh(servicio)

    # Attach catalog & evidencias for response
    servicio.catalogo = catalogo
    servicio.evidencias = []
    return servicio


@router.get("/servicios", response_model=list[ServicioContenedorOut])
async def listar_servicios(
    estado: EstadoServicio | None = Query(default=None),
    cliente_id: uuid.UUID | None = Query(default=None),
    contenedor_id: uuid.UUID | None = Query(default=None),
    patio_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.CLIENTE, RolUsuario.CUADRILLA, RolUsuario.SUPERVISOR, RolUsuario.ADMIN, RolUsuario.OPERADOR)),
) -> list[ServicioContenedor]:
    query = select(ServicioContenedor)

    if user.rol == RolUsuario.CLIENTE:
        query = query.where(ServicioContenedor.cliente_id == user.cliente_id)
    else:
        if cliente_id is not None:
            query = query.where(ServicioContenedor.cliente_id == cliente_id)
        if patio_id is not None:
            query = query.join(Contenedor, ServicioContenedor.contenedor_id == Contenedor.id).where(Contenedor.patio_id == patio_id)

    if estado is not None:
        query = query.where(ServicioContenedor.estado == estado)
    if contenedor_id is not None:
        query = query.where(ServicioContenedor.contenedor_id == contenedor_id)

    query = query.order_by(ServicioContenedor.solicitado_en.desc())
    result = await db.execute(query)
    servicios = list(result.scalars().all())

    # Populate catalogs and evidencias
    for s in servicios:
        cat_res = await db.execute(select(ServicioCatalogo).where(ServicioCatalogo.id == s.servicio_catalogo_id))
        s.catalogo = cat_res.scalar_one_or_none()
        ev_res = await db.execute(select(Evidencia).where(Evidencia.servicio_contenedor_id == s.id))
        s.evidencias = list(ev_res.scalars().all())

    return servicios


@router.post("/servicios/{servicio_id}/programar", response_model=ServicioContenedorOut)
async def programar_servicio(
    servicio_id: uuid.UUID,
    payload: ServicioContenedorProgramar,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_PROGRAMAR)),
) -> ServicioContenedor:
    res = await db.execute(select(ServicioContenedor).where(ServicioContenedor.id == servicio_id))
    servicio = res.scalar_one_or_none()
    if servicio is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Orden de servicio no encontrada")

    if servicio.estado != EstadoServicio.SOLICITADO:
        raise HTTPException(status.HTTP_409_CONFLICT, "Solo se pueden programar órdenes en estado solicitado")

    estado_anterior = servicio.estado.value
    servicio.estado = EstadoServicio.PROGRAMADO
    servicio.programado_para = payload.programado_para
    servicio.asignado_a = payload.asignado_a

    await db.flush()
    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="programar_servicio",
        entidad="servicios_contenedor",
        entidad_id=str(servicio.id),
        valor_anterior={"estado": estado_anterior},
        valor_nuevo={"estado": servicio.estado.value, "programado_para": str(payload.programado_para)},
    )
    await db.commit()
    await db.refresh(servicio)

    cat_res = await db.execute(select(ServicioCatalogo).where(ServicioCatalogo.id == servicio.servicio_catalogo_id))
    servicio.catalogo = cat_res.scalar_one_or_none()
    ev_res = await db.execute(select(Evidencia).where(Evidencia.servicio_contenedor_id == servicio.id))
    servicio.evidencias = list(ev_res.scalars().all())
    return servicio


@router.post("/servicios/{servicio_id}/iniciar", response_model=ServicioContenedorOut)
async def iniciar_servicio(
    servicio_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_GESTION_ORDEN)),
) -> ServicioContenedor:
    res = await db.execute(select(ServicioContenedor).where(ServicioContenedor.id == servicio_id))
    servicio = res.scalar_one_or_none()
    if servicio is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Orden de servicio no encontrada")

    if servicio.estado not in (EstadoServicio.SOLICITADO, EstadoServicio.PROGRAMADO):
        raise HTTPException(status.HTTP_409_CONFLICT, "La orden no está en estado solicitado o programado para iniciar")

    # Verify container is located or ready (not in solicitud_ingreso)
    cont_res = await db.execute(select(Contenedor).where(Contenedor.id == servicio.contenedor_id))
    contenedor = cont_res.scalar_one()
    if contenedor.estado == EstadoContenedor.SOLICITUD_INGRESO:
        raise HTTPException(status.HTTP_409_CONFLICT, "No se puede iniciar servicio en contenedor con solicitud de ingreso pendiente")

    estado_anterior = servicio.estado.value
    servicio.estado = EstadoServicio.EN_PROCESO
    servicio.iniciado_en = func.now()
    servicio.realizado_por = user.id

    # If container is not already en_servicio_especial, update container state
    if contenedor.estado != EstadoContenedor.EN_SERVICIO_ESPECIAL:
        contenedor.estado = EstadoContenedor.EN_SERVICIO_ESPECIAL

    await db.flush()
    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="iniciar_servicio",
        entidad="servicios_contenedor",
        entidad_id=str(servicio.id),
        valor_anterior={"estado": estado_anterior},
        valor_nuevo={"estado": servicio.estado.value},
        patio_id=contenedor.patio_id,
    )
    await db.commit()
    await db.refresh(servicio)

    cat_res = await db.execute(select(ServicioCatalogo).where(ServicioCatalogo.id == servicio.servicio_catalogo_id))
    servicio.catalogo = cat_res.scalar_one_or_none()
    ev_res = await db.execute(select(Evidencia).where(Evidencia.servicio_contenedor_id == servicio.id))
    servicio.evidencias = list(ev_res.scalars().all())
    return servicio


@router.post("/servicios/{servicio_id}/terminar", response_model=ServicioContenedorOut)
async def terminar_servicio(
    servicio_id: uuid.UUID,
    payload: ServicioContenedorTerminar,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_GESTION_ORDEN)),
) -> ServicioContenedor:
    res = await db.execute(select(ServicioContenedor).where(ServicioContenedor.id == servicio_id))
    servicio = res.scalar_one_or_none()
    if servicio is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Orden de servicio no encontrada")

    if servicio.estado != EstadoServicio.EN_PROCESO:
        raise HTTPException(status.HTTP_409_CONFLICT, "La orden no está en proceso")

    cat_res = await db.execute(select(ServicioCatalogo).where(ServicioCatalogo.id == servicio.servicio_catalogo_id))
    catalogo = cat_res.scalar_one()

    # Save any new evidence passed in payload
    if payload.evidencias:
        for url in payload.evidencias:
            ev = Evidencia(
                contenedor_id=servicio.contenedor_id,
                servicio_contenedor_id=servicio.id,
                url=url,
                tipo="servicio",
                creado_por=user.id,
            )
            db.add(ev)
        await db.flush()

    # Check requires evidence
    ev_check_res = await db.execute(select(Evidencia).where(Evidencia.servicio_contenedor_id == servicio.id))
    evidencias_list = list(ev_check_res.scalars().all())
    if catalogo.requiere_evidencia and not evidencias_list:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Este servicio requiere al menos una evidencia fotográfica para terminar")

    estado_anterior = servicio.estado.value
    servicio.estado = EstadoServicio.TERMINADO
    servicio.terminado_en = func.now()
    if payload.notas:
        servicio.notas = payload.notas

    # Check if container should return to UBICADO (if no other active services require moving/being en_servicio_especial)
    cont_res = await db.execute(select(Contenedor).where(Contenedor.id == servicio.contenedor_id))
    contenedor = cont_res.scalar_one()

    # Check if any other service is still in_proceso or programado/solicitado that keeps it
    other_active_res = await db.execute(
        select(ServicioContenedor).where(
            ServicioContenedor.contenedor_id == contenedor.id,
            ServicioContenedor.id != servicio.id,
            ServicioContenedor.estado.in_([EstadoServicio.EN_PROCESO, EstadoServicio.PROGRAMADO]),
        )
    )
    if not other_active_res.scalars().first():
        if contenedor.estado == EstadoContenedor.EN_SERVICIO_ESPECIAL:
            contenedor.estado = EstadoContenedor.UBICADO

    await db.flush()
    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="terminar_servicio",
        entidad="servicios_contenedor",
        entidad_id=str(servicio.id),
        valor_anterior={"estado": estado_anterior},
        valor_nuevo={"estado": servicio.estado.value},
        patio_id=contenedor.patio_id,
    )
    await db.commit()
    await db.refresh(servicio)

    servicio.catalogo = catalogo
    servicio.evidencias = evidencias_list
    return servicio


@router.post("/servicios/{servicio_id}/rechazar", response_model=ServicioContenedorOut)
async def rechazar_servicio(
    servicio_id: uuid.UUID,
    payload: ServicioContenedorMotivo,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_PROGRAMAR)),
) -> ServicioContenedor:
    res = await db.execute(select(ServicioContenedor).where(ServicioContenedor.id == servicio_id))
    servicio = res.scalar_one_or_none()
    if servicio is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Orden de servicio no encontrada")

    if servicio.estado != EstadoServicio.SOLICITADO:
        raise HTTPException(status.HTTP_409_CONFLICT, "Solo se pueden rechazar órdenes en estado solicitado")

    estado_anterior = servicio.estado.value
    servicio.estado = EstadoServicio.RECHAZADO
    servicio.motivo = payload.motivo

    await db.flush()
    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="rechazar_servicio",
        entidad="servicios_contenedor",
        entidad_id=str(servicio.id),
        valor_anterior={"estado": estado_anterior},
        valor_nuevo={"estado": servicio.estado.value, "motivo": payload.motivo},
    )
    await db.commit()
    await db.refresh(servicio)

    cat_res = await db.execute(select(ServicioCatalogo).where(ServicioCatalogo.id == servicio.servicio_catalogo_id))
    servicio.catalogo = cat_res.scalar_one_or_none()
    ev_res = await db.execute(select(Evidencia).where(Evidencia.servicio_contenedor_id == servicio.id))
    servicio.evidencias = list(ev_res.scalars().all())
    return servicio


@router.post("/servicios/{servicio_id}/cancelar", response_model=ServicioContenedorOut)
async def cancelar_servicio(
    servicio_id: uuid.UUID,
    payload: ServicioContenedorMotivo,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.CLIENTE, RolUsuario.SUPERVISOR, RolUsuario.ADMIN)),
) -> ServicioContenedor:
    res = await db.execute(select(ServicioContenedor).where(ServicioContenedor.id == servicio_id))
    servicio = res.scalar_one_or_none()
    if servicio is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Orden de servicio no encontrada")

    if user.rol == RolUsuario.CLIENTE:
        if servicio.cliente_id != user.cliente_id or servicio.estado != EstadoServicio.SOLICITADO:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No autorizado para cancelar esta orden")
    else:
        if servicio.estado not in (EstadoServicio.SOLICITADO, EstadoServicio.PROGRAMADO):
            raise HTTPException(status.HTTP_409_CONFLICT, "Solo se pueden cancelar órdenes en estado solicitado o programado")

    estado_anterior = servicio.estado.value
    servicio.estado = EstadoServicio.CANCELADO
    servicio.motivo = payload.motivo

    await db.flush()
    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="cancelar_servicio",
        entidad="servicios_contenedor",
        entidad_id=str(servicio.id),
        valor_anterior={"estado": estado_anterior},
        valor_nuevo={"estado": servicio.estado.value, "motivo": payload.motivo},
    )
    await db.commit()
    await db.refresh(servicio)

    cat_res = await db.execute(select(ServicioCatalogo).where(ServicioCatalogo.id == servicio.servicio_catalogo_id))
    servicio.catalogo = cat_res.scalar_one_or_none()
    ev_res = await db.execute(select(Evidencia).where(Evidencia.servicio_contenedor_id == servicio.id))
    servicio.evidencias = list(ev_res.scalars().all())
    return servicio
