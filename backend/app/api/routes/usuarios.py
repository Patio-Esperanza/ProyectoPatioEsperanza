import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.core.auditoria import registrar_auditoria
from app.core.security import hash_password
from app.db import get_db
from app.models.enums import RolUsuario
from app.models.ubicacion import Patio
from app.models.usuario import Usuario, UsuarioPatio
from app.schemas.patio import PatioOut
from app.schemas.usuario import UsuarioCreate, UsuarioOut

router = APIRouter()


async def _patios_por_usuario(
    db: AsyncSession, usuario_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[PatioOut]]:
    if not usuario_ids:
        return {}
    result = await db.execute(
        select(UsuarioPatio.usuario_id, Patio)
        .join(Patio, Patio.id == UsuarioPatio.patio_id)
        .where(UsuarioPatio.usuario_id.in_(usuario_ids))
    )
    agrupado: dict[uuid.UUID, list[PatioOut]] = {}
    for usuario_id, patio in result.all():
        agrupado.setdefault(usuario_id, []).append(PatioOut.model_validate(patio))
    return agrupado


def _a_usuario_out(usuario: Usuario, patios: list[PatioOut]) -> UsuarioOut:
    return UsuarioOut(
        id=usuario.id,
        nombre=usuario.nombre,
        email=usuario.email,
        tipo=usuario.tipo,
        activo=usuario.activo,
        patios=patios,
    )


@router.post("", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    payload: UsuarioCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.ADMIN)),
) -> UsuarioOut:
    if payload.tipo == RolUsuario.CLIENTE:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "El rol cliente no se crea desde este endpoint",
        )

    if payload.tipo != RolUsuario.ADMIN and not payload.patio_ids:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Este rol requiere al menos un patio asignado",
        )

    existente = await db.execute(select(Usuario).where(Usuario.email == payload.email))
    if existente.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email ya registrado")

    patios_out: list[PatioOut] = []
    if payload.patio_ids:
        patios_result = await db.execute(select(Patio).where(Patio.id.in_(payload.patio_ids)))
        patios_encontrados = list(patios_result.scalars().all())
        if {p.id for p in patios_encontrados} != set(payload.patio_ids):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "Uno o mas patio_ids no existen"
            )
        patios_out = [PatioOut.model_validate(p) for p in patios_encontrados]

    usuario = Usuario(
        nombre=payload.nombre,
        email=payload.email,
        password_hash=hash_password(payload.password),
        tipo=payload.tipo,
        activo=True,
    )
    db.add(usuario)
    await db.flush()

    for patio_id in payload.patio_ids:
        db.add(UsuarioPatio(usuario_id=usuario.id, patio_id=patio_id))
    await db.flush()

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="crear",
        entidad="usuarios",
        entidad_id=str(usuario.id),
        valor_anterior=None,
        valor_nuevo={"email": usuario.email, "tipo": usuario.tipo.value},
        patio_id=payload.patio_ids[0] if payload.patio_ids else None,
    )
    await db.commit()

    return _a_usuario_out(usuario, patios_out)


@router.get("", response_model=list[UsuarioOut])
async def listar_usuarios(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.ADMIN)),
) -> list[UsuarioOut]:
    result = await db.execute(select(Usuario))
    usuarios = list(result.scalars().all())
    patios_por_usuario = await _patios_por_usuario(db, [u.id for u in usuarios])
    return [_a_usuario_out(u, patios_por_usuario.get(u.id, [])) for u in usuarios]
