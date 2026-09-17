import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import TipoContenedor


class Patio(Base):
    __tablename__ = "patios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="America/Mexico_City")
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Carril(Base):
    __tablename__ = "carriles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patios.id"), nullable=False)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tipo_teorico: Mapped[TipoContenedor | None] = mapped_column(
        Enum(TipoContenedor, name="tipo_contenedor", values_callable=lambda obj: [e.value for e in obj]),
        nullable=True,
    )

    __table_args__ = (UniqueConstraint("patio_id", "codigo", name="uq_carril_patio_codigo"),)


class Tramo(Base):
    __tablename__ = "tramos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    carril_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("carriles.id"), nullable=False)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (UniqueConstraint("carril_id", "codigo", name="uq_tramo_carril_codigo"),)


class Tira(Base):
    __tablename__ = "tiras"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tramo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tramos.id"), nullable=False)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (UniqueConstraint("tramo_id", "codigo", name="uq_tira_tramo_codigo"),)


class Ubicacion(Base):
    __tablename__ = "ubicaciones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tira_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tiras.id"), nullable=False)
    nivel: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    capacidad_peso_kg: Mapped[int] = mapped_column(Integer, nullable=False, default=30000)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("tira_id", "nivel", name="uq_ubicacion_tira_nivel"),
        CheckConstraint("nivel BETWEEN 1 AND 5", name="ck_ubicacion_nivel_1_5"),
    )
