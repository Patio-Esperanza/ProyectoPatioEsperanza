import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.core.auditoria import registrar_auditoria
from app.core.sellos import normalizar_sellos
from app.db import get_db
from app.models.contenedor import Contenedor, Movimiento
from app.models.evidencia import Evidencia
from app.models.inspeccion import Inspeccion
from app.models.enums import EstadoContenedor, RolUsuario, TipoMovimiento
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion
from app.schemas.contenedor import ContenedorOut
from app.schemas.porteria import PorteriaIngresoCreate, PorteriaIngresoResponse
from app.schemas.ubicacion import SugerenciaUbicacionResponse
from app.services.ubicacion_algoritmo import sugerir_ubicaciones_multiples
from app.jobs.webhooks_socio import registrar_evento_socio

router = APIRouter()

_ROLES_PORTERIA = (RolUsuario.GUARDIA, RolUsuario.SUPERVISOR, RolUsuario.ADMIN)


@router.get("/buscar", response_model=list[ContenedorOut])
async def buscar_solicitudes_porteria(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_PORTERIA)),
) -> list[Contenedor]:
    if user.rol == RolUsuario.GUARDIA and not user.patios:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Guardia sin patios asignados")

    query = select(Contenedor).where(
        Contenedor.estado == EstadoContenedor.SOLICITUD_INGRESO,
        Contenedor.pin_confirmacion.is_not(None),
    )
    if user.rol == RolUsuario.GUARDIA:
        query = query.where(Contenedor.patio_id.in_(user.patios))

    query = query.where(
        (Contenedor.pin_confirmacion == q) | (Contenedor.numero_contenedor.ilike(f"%{q}%"))
    )

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/ingresos", response_model=PorteriaIngresoResponse, status_code=status.HTTP_201_CREATED)
async def registrar_ingreso_porteria(
    payload: PorteriaIngresoCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_PORTERIA)),
) -> PorteriaIngresoResponse:
    if user.rol == RolUsuario.GUARDIA and not user.patios:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Guardia sin patios asignados")

    query = select(Contenedor).where(
        Contenedor.pin_confirmacion == payload.pin,
        Contenedor.estado == EstadoContenedor.SOLICITUD_INGRESO,
    )
    if user.rol == RolUsuario.GUARDIA:
        query = query.where(Contenedor.patio_id.in_(user.patios))

    result = await db.execute(query)
    contenedor = result.scalar_one_or_none()
    if contenedor is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "El PIN no corresponde a ninguna solicitud de ingreso pendiente en este patio",
        )

    if not payload.evidencias:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Se requiere al menos una evidencia fotográfica")

    placas_coinciden = None
    if contenedor.transporte_esperado and isinstance(contenedor.transporte_esperado, dict):
        esperadas = contenedor.transporte_esperado.get("placas")
        if esperadas and payload.placas:
            placas_coinciden = esperadas.strip().upper() == payload.placas.strip().upper()

    danos_dict = payload.danos or {}
    if placas_coinciden is not None:
        danos_dict["placas_coinciden"] = placas_coinciden

    inspeccion = Inspeccion(
        contenedor_id=contenedor.id,
        placas=payload.placas,
        operador=payload.operador,
        sellos=payload.sellos or contenedor.sellos,
        danos=danos_dict,
        notas=payload.notas,
    )
    db.add(inspeccion)
    await db.flush()

    for url in payload.evidencias:
        evidencia = Evidencia(
            contenedor_id=contenedor.id,
            inspeccion_id=inspeccion.id,
            url=url,
            tipo="ingreso",
            creado_por=user.id,
        )
        db.add(evidencia)

    movimiento = Movimiento(
        contenedor_id=contenedor.id,
        patio_id=contenedor.patio_id,
        tipo=TipoMovimiento.INGRESO,
        operador_id=user.id,
    )
    db.add(movimiento)

    contenedor.estado = EstadoContenedor.INGRESADO
    if payload.sellos:
        contenedor.sellos = normalizar_sellos(payload.sellos)
    contenedor.pin_confirmacion = None

    await registrar_evento_socio(db, contenedor, "contenedor.ingresado")
    await db.flush()

    patio_result = await db.execute(select(Patio).where(Patio.id == contenedor.patio_id))
    patio = patio_result.scalar_one()

    ref_ubicacion_id = patio.ubicacion_entrada_id
    if ref_ubicacion_id is None:
        ref_res = await db.execute(
            select(Ubicacion)
            .join(Tira, Ubicacion.tira_id == Tira.id)
            .join(Tramo, Tira.tramo_id == Tramo.id)
            .join(Carril, Tramo.carril_id == Carril.id)
            .where(Carril.patio_id == contenedor.patio_id, Ubicacion.activo.is_(True))
            .limit(1)
        )
        ref_loc = ref_res.scalar_one_or_none()
        if ref_loc:
            ref_ubicacion_id = ref_loc.id

    sugerencias = []
    if ref_ubicacion_id:
        try:
            candidatos = await sugerir_ubicaciones_multiples(
                db,
                patio_id=contenedor.patio_id,
                contenedor=contenedor,
                punto_referencia_ubicacion_id=ref_ubicacion_id,
                limit=3,
            )
            sugerencias = [
                SugerenciaUbicacionResponse(
                    ubicacion_id=c.ubicacion_id,
                    codigo=c.codigo,
                    costo=c.costo,
                    tira_id=c.tira_id,
                    nivel=c.nivel,
                )
                for c in candidatos
            ]
        except Exception:
            pass

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="ingresar",
        entidad="contenedores",
        entidad_id=str(contenedor.id),
        valor_anterior={"estado": EstadoContenedor.SOLICITUD_INGRESO.value},
        valor_nuevo={"estado": contenedor.estado.value},
        patio_id=contenedor.patio_id,
    )
    await db.commit()
    await db.refresh(contenedor)

    return PorteriaIngresoResponse(
        contenedor=contenedor,
        sugerencias=sugerencias,
    )
