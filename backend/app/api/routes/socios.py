import secrets
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field, field_validator, model_validator

from app.api.deps import CurrentSocio, verificar_api_key
from app.core.iso6346 import validar_iso6346
from app.core.sellos import normalizar_sellos
from app.db import get_db
from app.models.contenedor import Contenedor
from app.models.enums import EstadoContenedor, TamanoContenedor, TipoContenedor, TipoCliente
from app.schemas.contenedor import ContenedorOut
from app.services.socio_service import resolver_o_crear_cliente

router = APIRouter()


class ClienteSocioCreate(BaseModel):
    tipo: TipoCliente
    rfc: str
    nombre: str


class AduanaSocioCreate(BaseModel):
    agencia: str | None = None
    num_refe: str | None = None


class TransporteSocioCreate(BaseModel):
    operador: str | None = None
    telefono: str | None = None
    placas: str | None = None
    numero_economico: str | None = None


class SolicitudIngresoSocioCreate(BaseModel):
    idempotency_key: str | None = None
    referencia_externa: str | None = None
    patio_id: uuid.UUID
    numero_contenedor: str
    tipo: TipoContenedor
    tamano: TamanoContenedor
    tipo_iso: str | None = None
    peso_kg: int
    sellos: str | None = None
    sin_sello: bool = False
    cliente: ClienteSocioCreate
    aduana: AduanaSocioCreate | None = None
    transporte: TransporteSocioCreate | None = None
    fecha_estimada_llegada: datetime | None = None

    @field_validator("numero_contenedor")
    @classmethod
    def validar_contenedor(cls, v: str) -> str:
        v_clean = v.strip().upper()
        if not validar_iso6346(v_clean):
            raise ValueError("Número de contenedor inválido (ISO 6346)")
        return v_clean

    @field_validator("sellos")
    @classmethod
    def validar_sellos(cls, v: str | None) -> str | None:
        return normalizar_sellos(v)

    @model_validator(mode="after")
    def validar_sello_lleno(self) -> "SolicitudIngresoSocioCreate":
        if self.tipo == TipoContenedor.LLENO and not self.sin_sello and not self.sellos:
            raise ValueError("Un contenedor lleno requiere sello; si no tiene, marque sin_sello=True")
        return self


class SolicitudIngresoSocioUpdate(BaseModel):
    transporte: TransporteSocioCreate | None = None
    aduana: AduanaSocioCreate | None = None
    referencia_externa: str | None = None
    fecha_estimada_llegada: datetime | None = None


class ContenedorSocioOut(ContenedorOut):
    pin: str | None = Field(default=None, validation_alias="pin_confirmacion")
    referencia_externa: str | None = None
    transporte_esperado: dict | None = None
    datos_aduana: dict | None = None


@router.post("/v1/solicitudes-ingreso", response_model=ContenedorSocioOut, status_code=status.HTTP_201_CREATED)
async def crear_solicitud_ingreso_socio(
    payload: SolicitudIngresoSocioCreate,
    socio: CurrentSocio = Depends(verificar_api_key),
    db: AsyncSession = Depends(get_db),
) -> Contenedor:
    if payload.patio_id not in socio.patios_permitidos:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patio no permitido para esta credencial de socio",
        )

    if payload.idempotency_key:
        stmt = select(Contenedor).where(
            Contenedor.credencial_socio_id == socio.id,
            Contenedor.idempotency_key == payload.idempotency_key,
        )
        result = await db.execute(stmt)
        existente = result.scalar_one_or_none()
        if existente:
            return existente

    cliente = await resolver_o_crear_cliente(
        db,
        tipo=payload.cliente.tipo,
        rfc=payload.cliente.rfc,
        nombre=payload.cliente.nombre,
    )

    pin = f"{secrets.randbelow(10000):04d}"

    contenedor = Contenedor(
        numero_contenedor=payload.numero_contenedor,
        tipo=payload.tipo,
        tamano=payload.tamano,
        patio_id=payload.patio_id,
        cliente_id=cliente.id,
        peso_kg=payload.peso_kg,
        sellos=payload.sellos,
        estado=EstadoContenedor.SOLICITUD_INGRESO,
        pin_confirmacion=pin,
        origen="socio",
        credencial_socio_id=socio.id,
        idempotency_key=payload.idempotency_key,
        referencia_externa=payload.referencia_externa,
        datos_aduana=payload.aduana.model_dump() if payload.aduana else None,
        transporte_esperado=payload.transporte.model_dump() if payload.transporte else None,
        fecha_estimada_salida=payload.fecha_estimada_llegada,
        peso_por_confirmar=False,
    )

    db.add(contenedor)
    try:
        await db.commit()
        await db.refresh(contenedor)
    except IntegrityError:
        await db.rollback()
        if payload.idempotency_key:
            stmt = select(Contenedor).where(
                Contenedor.credencial_socio_id == socio.id,
                Contenedor.idempotency_key == payload.idempotency_key,
            )
            result = await db.execute(stmt)
            existente = result.scalar_one_or_none()
            if existente:
                return existente
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflicto de unicidad al registrar la solicitud de ingreso",
        )

    return contenedor


@router.patch("/v1/solicitudes-ingreso/{id}", response_model=ContenedorSocioOut)
async def actualizar_solicitud_ingreso_socio(
    id: uuid.UUID,
    payload: SolicitudIngresoSocioUpdate,
    socio: CurrentSocio = Depends(verificar_api_key),
    db: AsyncSession = Depends(get_db),
) -> Contenedor:
    stmt = select(Contenedor).where(
        Contenedor.id == id,
        Contenedor.credencial_socio_id == socio.id,
    )
    result = await db.execute(stmt)
    contenedor = result.scalar_one_or_none()

    if contenedor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud no encontrada")

    if contenedor.estado != EstadoContenedor.SOLICITUD_INGRESO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La solicitud ya no está en estado solicitud_ingreso",
        )

    if payload.transporte is not None:
        contenedor.transporte_esperado = payload.transporte.model_dump()
    if payload.aduana is not None:
        contenedor.datos_aduana = payload.aduana.model_dump()
    if payload.referencia_externa is not None:
        contenedor.referencia_externa = payload.referencia_externa
    if payload.fecha_estimada_llegada is not None:
        contenedor.fecha_estimada_salida = payload.fecha_estimada_llegada

    await db.commit()
    await db.refresh(contenedor)
    return contenedor


@router.post("/v1/solicitudes-ingreso/{id}/cancelar", response_model=ContenedorSocioOut)
async def cancelar_solicitud_ingreso_socio(
    id: uuid.UUID,
    socio: CurrentSocio = Depends(verificar_api_key),
    db: AsyncSession = Depends(get_db),
) -> Contenedor:
    stmt = select(Contenedor).where(
        Contenedor.id == id,
        Contenedor.credencial_socio_id == socio.id,
    )
    result = await db.execute(stmt)
    contenedor = result.scalar_one_or_none()

    if contenedor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud no encontrada")

    if contenedor.estado != EstadoContenedor.SOLICITUD_INGRESO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La solicitud ya no está en estado solicitud_ingreso",
        )

    contenedor.estado = EstadoContenedor.RECHAZADO
    contenedor.pin_confirmacion = None

    await db.commit()
    await db.refresh(contenedor)
    return contenedor


@router.get("/v1/contenedores/{id}", response_model=ContenedorSocioOut)
async def obtener_contenedor_socio(
    id: uuid.UUID,
    socio: CurrentSocio = Depends(verificar_api_key),
    db: AsyncSession = Depends(get_db),
) -> Contenedor:
    stmt = select(Contenedor).where(
        Contenedor.id == id,
        Contenedor.credencial_socio_id == socio.id,
    )
    result = await db.execute(stmt)
    contenedor = result.scalar_one_or_none()

    if contenedor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contenedor no encontrado")

    return contenedor
