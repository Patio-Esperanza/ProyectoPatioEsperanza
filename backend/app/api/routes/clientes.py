from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.core.auditoria import registrar_auditoria
from app.db import get_db
from app.models.cliente import Cliente
from app.models.enums import RolUsuario
from app.schemas.cliente import ClienteCreate, ClienteOut

router = APIRouter()


@router.post("", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
async def crear_cliente(
    payload: ClienteCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.ADMIN)),
) -> Cliente:
    cliente = Cliente(razon_social=payload.razon_social, rfc=payload.rfc, tipo=payload.tipo, activo=True)
    db.add(cliente)
    await db.flush()

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="crear",
        entidad="clientes",
        entidad_id=str(cliente.id),
        valor_anterior=None,
        valor_nuevo={"razon_social": cliente.razon_social, "rfc": cliente.rfc},
        patio_id=None,
    )
    await db.commit()
    return cliente


@router.get("", response_model=list[ClienteOut])
async def listar_clientes(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.ADMIN)),
) -> list[Cliente]:
    result = await db.execute(select(Cliente))
    return list(result.scalars().all())
