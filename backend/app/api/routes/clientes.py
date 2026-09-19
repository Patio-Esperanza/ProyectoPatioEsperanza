import random
import string
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.core.auditoria import registrar_auditoria
from app.core.email import enviar_correo
from app.core.security import hash_password
from app.db import get_db
from app.models.cliente import Cliente
from app.models.enums import RolUsuario
from app.models.usuario import Usuario
from app.schemas.cliente import ClienteCreate, ClienteOut, ClienteRegistro, ClienteVerificar

router = APIRouter()

_CODIGO_EXPIRA_MINUTOS = 15


def _generar_codigo() -> str:
    return "".join(random.choices(string.digits, k=6))


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


@router.post("/registro", status_code=status.HTTP_201_CREATED)
async def registrar_cliente(
    payload: ClienteRegistro,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    existente_result = await db.execute(select(Usuario).where(Usuario.email == payload.email))
    existente = existente_result.scalar_one_or_none()
    if existente is not None and existente.activo:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email ya registrado")

    cliente_result = await db.execute(
        select(Cliente).where(Cliente.rfc == payload.rfc, Cliente.activo.is_(True))
    )
    cliente = cliente_result.scalar_one_or_none()

    codigo = _generar_codigo()
    expira = datetime.now(timezone.utc) + timedelta(minutes=_CODIGO_EXPIRA_MINUTOS)

    if existente is not None:
        existente.nombre = payload.nombre
        existente.password_hash = hash_password(payload.password)
        existente.cliente_id = cliente.id if cliente else None
        existente.codigo_verificacion = codigo
        existente.codigo_verificacion_expira = expira
    else:
        db.add(
            Usuario(
                nombre=payload.nombre,
                email=payload.email,
                password_hash=hash_password(payload.password),
                tipo=RolUsuario.CLIENTE,
                cliente_id=cliente.id if cliente else None,
                activo=False,
                codigo_verificacion=codigo,
                codigo_verificacion_expira=expira,
            )
        )
    await db.commit()

    try:
        enviar_correo(
            payload.email,
            "Código de verificación — Patio Esperanza",
            f"<p>Tu código de verificación es <strong>{codigo}</strong>. "
            f"Expira en {_CODIGO_EXPIRA_MINUTOS} minutos.</p>",
        )
    except Exception as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "No se pudo enviar el correo de verificación, intenta de nuevo",
        ) from exc

    return {"detail": "Código de verificación enviado"}


@router.post("/verificar")
async def verificar_cliente(
    payload: ClienteVerificar,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(select(Usuario).where(Usuario.email == payload.email))
    usuario = result.scalar_one_or_none()
    if usuario is None or usuario.codigo_verificacion is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Código incorrecto")

    if usuario.codigo_verificacion != payload.codigo:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Código incorrecto")

    if (
        usuario.codigo_verificacion_expira is None
        or usuario.codigo_verificacion_expira < datetime.now(timezone.utc)
    ):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Código expirado, solicita uno nuevo")

    usuario.codigo_verificacion = None
    usuario.codigo_verificacion_expira = None

    if usuario.cliente_id is None:
        await db.commit()
        return {"detail": "Código correcto. Tu empresa (RFC) no está registrada, contacta al administrador"}

    usuario.activo = True
    await db.commit()
    return {"detail": "Cuenta activada"}
