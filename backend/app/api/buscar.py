import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.api.deps import CurrentUser, get_current_user
from app.core.ubicaciones import etiqueta_ubicacion
from app.db import get_db
from app.models.cliente import Cliente
from app.models.contenedor import Contenedor, Movimiento
from app.models.enums import RolUsuario, TipoMovimiento
from app.models.ubicacion import Ubicacion
from pydantic import BaseModel

router = APIRouter()


class ResultadoBusquedaOut(BaseModel):
    id: uuid.UUID
    numero_contenedor: str
    cliente_nombre: str | None = None
    estado: str
    ubicacion_etiqueta: str | None = None
    dias_en_patio: int = 0
    remanejos: int = 0


@router.get("", response_model=list[ResultadoBusquedaOut])
async def buscar_global(
    q: str = Query(..., min_length=1),
    patio_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> list[ResultadoBusquedaOut]:
    q_stripped = q.strip()
    if len(q_stripped) < 4:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "La busqueda requiere al menos 4 caracteres",
        )

    fecha_ingreso_sq = (
        select(func.max(Movimiento.ts))
        .where(
            Movimiento.contenedor_id == Contenedor.id,
            Movimiento.tipo == TipoMovimiento.INGRESO,
        )
        .correlate(Contenedor)
        .scalar_subquery()
    )

    UbicacionSuperior = aliased(Ubicacion)
    remanejos_sq = (
        select(func.count(Contenedor.id))
        .select_from(Contenedor)
        .join(UbicacionSuperior, Contenedor.ubicacion_id == UbicacionSuperior.id)
        .where(
            UbicacionSuperior.tira_id == Ubicacion.tira_id,
            UbicacionSuperior.nivel > Ubicacion.nivel,
        )
        .correlate(Contenedor, Ubicacion)
        .scalar_subquery()
    )

    query = (
        select(Contenedor, Cliente.razon_social, Ubicacion, fecha_ingreso_sq, remanejos_sq)
        .outerjoin(Cliente, Contenedor.cliente_id == Cliente.id)
        .outerjoin(Ubicacion, Contenedor.ubicacion_id == Ubicacion.id)
        .where(Contenedor.numero_contenedor.ilike(f"%{q_stripped}%"))
    )

    if user.rol == RolUsuario.CLIENTE:
        if user.cliente_id is not None:
            query = query.where(Contenedor.cliente_id == user.cliente_id)
        else:
            return []
    else:
        if patio_id is not None:
            query = query.where(Contenedor.patio_id == patio_id)

    query = query.limit(10)
    result = await db.execute(query)
    rows = result.all()

    now = datetime.datetime.now(datetime.timezone.utc)
    resultados = []
    for contenedor, cliente_nombre, ubicacion, fecha_ingreso, remanejos in rows:
        etiqueta = None
        if ubicacion is not None:
            etiqueta = etiqueta_ubicacion(ubicacion).corta

        dias = 0
        if fecha_ingreso is not None:
            if fecha_ingreso.tzinfo is None:
                fecha_ingreso = fecha_ingreso.replace(tzinfo=datetime.timezone.utc)
            delta = now - fecha_ingreso
            dias = max(0, delta.days)
        elif contenedor.created_at is not None:
            c_at = contenedor.created_at
            if c_at.tzinfo is None:
                c_at = c_at.replace(tzinfo=datetime.timezone.utc)
            delta = now - c_at
            dias = max(0, delta.days)

        resultados.append(
            ResultadoBusquedaOut(
                id=contenedor.id,
                numero_contenedor=contenedor.numero_contenedor,
                cliente_nombre=cliente_nombre,
                estado=contenedor.estado.value if hasattr(contenedor.estado, "value") else str(contenedor.estado),
                ubicacion_etiqueta=etiqueta,
                dias_en_patio=dias,
                remanejos=remanejos or 0,
            )
        )

    return resultados
