import datetime
import uuid

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, Text, and_, Table, Column, Date
from sqlalchemy.dialects.postgresql import JSONB, UUID
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
    # Código del sello de seguridad. `NULL` cuando el contenedor no trae sello:
    # la interfaz muestra entonces la leyenda "S/N". Varios sellos se capturan
    # separados por coma en este mismo campo.
    sellos: Mapped[str | None] = mapped_column(String(120), nullable=True)
    fecha_estimada_salida: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pin_confirmacion: Mapped[str | None] = mapped_column(String(4), nullable=True)
    pin_verificado_en: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pin_verificado_por: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True
    )
    fecha_deseada_salida: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    salida_solicitada_en: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pin_salida_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pin_salida_intentos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fecha_salida: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingresado_en: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    origen: Mapped[str | None] = mapped_column(String(50), nullable=True)
    credencial_socio_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("credenciales_socio.id"), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    referencia_externa: Mapped[str | None] = mapped_column(String(100), nullable=True)
    datos_aduana: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    transporte_esperado: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    peso_por_confirmar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index(
            "uq_contenedor_ubicacion_activa",
            "ubicacion_id",
            unique=True,
            postgresql_where=(ubicacion_id.is_not(None)),
        ),
        Index(
            "uq_contenedor_activo",
            "numero_contenedor",
            unique=True,
            postgresql_where=and_(
                estado != EstadoContenedor.DESPACHADO,
                estado != EstadoContenedor.RECHAZADO,
            ),
        ),
        Index(
            "uq_contenedor_socio_idempotency",
            "credencial_socio_id",
            "idempotency_key",
            unique=True,
            postgresql_where=(idempotency_key.is_not(None)),
        ),
        CheckConstraint(
            "estado != 'despachado' OR ubicacion_id IS NULL",
            name="ck_despachado_sin_ubicacion",
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


class InventarioDiario(Base):
    __tablename__ = "inventario_diario"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    patio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patios.id"), nullable=False)
    contenedor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contenedores.id"), nullable=False)
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=True)
    ubicacion_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ubicaciones.id"), nullable=True)
    estado: Mapped[str] = mapped_column(String(50), nullable=False)
    dias_estancia: Mapped[int] = mapped_column(Integer, nullable=False)


v_estancias_table = Table(
    "v_estancias",
    Base.metadata,
    Column("contenedor_id", UUID(as_uuid=True), primary_key=True),
    Column("patio_id", UUID(as_uuid=True)),
    Column("cliente_id", UUID(as_uuid=True)),
    Column("ingresado_en", DateTime(timezone=True)),
    Column("fecha_salida", DateTime(timezone=True)),
    Column("zona_horaria", String),
    Column("dias_estancia", Integer),
    Column("dias_libres", Integer),
    Column("dias_cobrables", Integer),
    extend_existing=True,
)
