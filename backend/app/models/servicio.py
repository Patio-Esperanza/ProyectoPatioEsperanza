import datetime
import enum
import uuid

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


class EstadoServicio(str, enum.Enum):
    SOLICITADO = "solicitado"
    PROGRAMADO = "programado"
    EN_PROCESO = "en_proceso"
    TERMINADO = "terminado"
    RECHAZADO = "rechazado"
    CANCELADO = "cancelado"


class ServicioCatalogo(Base):
    __tablename__ = "servicios_catalogo"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patio_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("patios.id"), nullable=True)
    codigo: Mapped[str] = mapped_column(String(10), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    requiere_evidencia: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    bloquea_salida: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requiere_mover: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requiere_unidad_relacionada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cliente_puede_solicitar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("uq_servicio_catalogo_patio_codigo", "patio_id", "codigo", unique=True),
    )


class UnidadRelacionadaTipo(str, enum.Enum):
    CONTENEDOR = "contenedor"
    CAJA_SECA = "caja_seca"


class ServicioContenedor(Base):
    __tablename__ = "servicios_contenedor"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contenedor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contenedores.id"), nullable=False)
    servicio_catalogo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("servicios_catalogo.id"), nullable=False)
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=True)
    estado: Mapped[EstadoServicio] = mapped_column(
        Enum(EstadoServicio, name="estado_servicio", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=EstadoServicio.SOLICITADO,
    )
    solicitado_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    asignado_a: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    realizado_por: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    programado_para: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    solicitado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    iniciado_en: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    terminado_en: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Segunda unidad (solo para traspaleo - TRA)
    unidad_relacionada_tipo: Mapped[UnidadRelacionadaTipo | None] = mapped_column(
        Enum(UnidadRelacionadaTipo, name="unidad_relacionada_tipo", values_callable=lambda obj: [e.value for e in obj]),
        nullable=True,
    )
    contenedor_relacionado_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contenedores.id"), nullable=True)
    unidad_relacionada_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)