import datetime
import uuid

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base
from app.models.enums import EstadoContenedor, TamanoContenedor, TipoContenedor, TipoMovimiento


class Contenedor(Base):
    __tablename__ = "contenedores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero_contenedor: Mapped[str] = mapped_column(String(11), nullable=False)
    tipo: Mapped[TipoContenedor] = mapped_column(
        Enum(TipoContenedor, name="tipo_contenedor", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    tamano: Mapped[TamanoContenedor] = mapped_column(
        Enum(TamanoContenedor, name="tamano_contenedor", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=True)
    patio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patios.id"), nullable=False)
    ubicacion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ubicaciones.id"), nullable=True
    )
    estado: Mapped[EstadoContenedor] = mapped_column(
        Enum(EstadoContenedor, name="estado_contenedor", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    peso_kg: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_estimada_salida: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pin_confirmacion: Mapped[str | None] = mapped_column(String(4), nullable=True)
    pin_verificado_en: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pin_verificado_por: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index(
            "uq_contenedor_ubicacion_activa",
            "ubicacion_id",
            unique=True,
            postgresql_where=(ubicacion_id.is_not(None)),
        ),
    )


class Movimiento(Base):
    __tablename__ = "movimientos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contenedor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contenedores.id"), nullable=False)
    patio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patios.id"), nullable=False)
    tipo: Mapped[TipoMovimiento] = mapped_column(
        Enum(TipoMovimiento, name="tipo_movimiento", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    ubicacion_origen_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ubicaciones.id"), nullable=True
    )
    ubicacion_destino_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ubicaciones.id"), nullable=True
    )
    operador_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    ts: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    override_manual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    score_sugerido: Mapped[float | None] = mapped_column(nullable=True)
    score_elegido: Mapped[float | None] = mapped_column(nullable=True)
    motivo_override: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_movimiento_contenedor_ts", "contenedor_id", "ts"),)
