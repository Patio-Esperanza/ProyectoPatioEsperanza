import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.core.auditoria import registrar_auditoria
from app.db import get_db
from app.models.enums import RolUsuario
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion
from app.schemas.mapa import MapaPatioOut
from app.schemas.patio import (
    LayoutPatioCreate,
    LayoutPatioOut,
    PatioCreate,
    PatioEntradaUpdate,
    PatioOut,
    PatioUpdate,
)
from app.services.mapa_patio import obtener_mapa
from app.services.patio_layout import sembrar_layout_uniforme

router = APIRouter()


@router.post("", response_model=PatioOut, status_code=status.HTTP_201_CREATED)
async def crear_patio(
    payload: PatioCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.ADMIN)),
) -> Patio:
    patio = Patio(
        nombre=payload.nombre,
        codigo=payload.codigo,
        anticipacion_minima_horas=payload.anticipacion_minima_horas,
    )
    db.add(patio)
    await db.flush()

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="crear",
        entidad="patios",
        entidad_id=str(patio.id),
        valor_anterior=None,
        valor_nuevo={"nombre": patio.nombre, "codigo": patio.codigo},
        patio_id=patio.id,
    )
    await db.commit()
    return patio


@router.get("", response_model=list[PatioOut])
async def listar_patios(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> list[Patio]:
    result = await db.execute(select(Patio))
    return list(result.scalars().all())


@router.patch("/{patio_id}", response_model=PatioOut)
async def actualizar_patio(
    patio_id: str,
    payload: PatioUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.ADMIN)),
) -> Patio:
    result = await db.execute(select(Patio).where(Patio.id == patio_id))
    patio = result.scalar_one_or_none()
    if patio is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patio no encontrado")

    valor_anterior = patio.anticipacion_minima_horas
    patio.anticipacion_minima_horas = payload.anticipacion_minima_horas

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="actualizar",
        entidad="patios",
        entidad_id=str(patio.id),
        valor_anterior={"anticipacion_minima_horas": valor_anterior},
        valor_nuevo={"anticipacion_minima_horas": patio.anticipacion_minima_horas},
        patio_id=patio.id,
    )
    await db.commit()
    await db.refresh(patio)
    return patio


@router.patch("/{patio_id}/entrada", response_model=PatioOut)
async def fijar_entrada_patio(
    patio_id: uuid.UUID,
    payload: PatioEntradaUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.ADMIN)),
) -> Patio:
    result = await db.execute(select(Patio).where(Patio.id == patio_id))
    patio = result.scalar_one_or_none()
    if patio is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patio no encontrado")

    ubicacion_result = await db.execute(
        select(Ubicacion)
        .join(Tira, Tira.id == Ubicacion.tira_id)
        .join(Tramo, Tramo.id == Tira.tramo_id)
        .join(Carril, Carril.id == Tramo.carril_id)
        .where(Carril.patio_id == patio_id, Ubicacion.codigo == payload.codigo)
    )
    ubicacion = ubicacion_result.scalars().first()
    if ubicacion is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Ubicacion de entrada no encontrada en este patio"
        )

    valor_anterior = patio.ubicacion_entrada_id
    patio.ubicacion_entrada_id = ubicacion.id

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="fijar_entrada",
        entidad="patios",
        entidad_id=str(patio.id),
        valor_anterior={
            "ubicacion_entrada_id": str(valor_anterior) if valor_anterior else None
        },
        valor_nuevo={"ubicacion_entrada_id": str(ubicacion.id), "codigo": ubicacion.codigo},
        patio_id=patio.id,
    )
    await db.commit()
    await db.refresh(patio)
    return patio


_ROLES_MAPA = (RolUsuario.OPERADOR, RolUsuario.SUPERVISOR, RolUsuario.ADMIN)


@router.get("/{patio_id}/mapa", response_model=MapaPatioOut)
async def mapa_patio(
    patio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_MAPA)),
) -> MapaPatioOut:
    existe = await db.execute(select(Patio.id).where(Patio.id == patio_id))
    if existe.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patio no encontrado")
    return await obtener_mapa(db, patio_id)


@router.post("/{patio_id}/layout", response_model=LayoutPatioOut)
async def configurar_layout_patio(
    patio_id: uuid.UUID,
    payload: LayoutPatioCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.ADMIN)),
) -> LayoutPatioOut:
    result = await db.execute(select(Patio).where(Patio.id == patio_id))
    patio = result.scalar_one_or_none()
    if patio is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patio no encontrado")

    carriles_creados, carriles_saltados, ubicaciones_creadas = await sembrar_layout_uniforme(
        db, patio, payload.carriles, payload.tramos, payload.tiras, payload.niveles
    )

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="configurar_layout",
        entidad="patios",
        entidad_id=str(patio.id),
        valor_anterior=None,
        valor_nuevo={
            "carriles_creados": carriles_creados,
            "carriles_saltados": carriles_saltados,
            "ubicaciones_creadas": ubicaciones_creadas,
        },
        patio_id=patio.id,
    )
    await db.commit()
    return LayoutPatioOut(
        carriles_creados=carriles_creados,
        carriles_saltados=carriles_saltados,
        ubicaciones_creadas=ubicaciones_creadas,
    )
