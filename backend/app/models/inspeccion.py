import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class Inspeccion(Base):
    __tablename__ = "inspecciones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contenedor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contenedores.id"), nullable=False)
    movimiento_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("movimientos.id"), nullable=True)
    placas: Mapped[str | None] = mapped_column(String(20), nullable=True)
    operador: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sellos: Mapped[str | None] = mapped_column(String(120), nullable=True)
    danos: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
