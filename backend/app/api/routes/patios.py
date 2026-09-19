from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.core.auditoria import registrar_auditoria
from app.db import get_db
from app.models.enums import RolUsuario
from app.models.ubicacion import Patio
from app.schemas.patio import PatioCreate, PatioOut, PatioUpdate

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
