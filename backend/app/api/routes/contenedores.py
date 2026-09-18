from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.core.auditoria import registrar_auditoria
from app.db import get_db
from app.models.contenedor import Contenedor
from app.models.enums import EstadoContenedor, RolUsuario
from app.schemas.contenedor import ContenedorCreate, ContenedorOut

router = APIRouter()

_ROLES_ESCRITURA = (RolUsuario.OPERADOR, RolUsuario.SUPERVISOR, RolUsuario.ADMIN)


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
