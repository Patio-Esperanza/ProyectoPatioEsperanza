import datetime
import uuid

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class Auditoria(Base):
    __tablename__ = "auditoria"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ts: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    rol: Mapped[str] = mapped_column(String(30), nullable=False)
    ip: Mapped[str] = mapped_column(String(45), nullable=False)
    dispositivo: Mapped[str] = mapped_column(String(200), nullable=False)
    accion: Mapped[str] = mapped_column(String(50), nullable=False)
    entidad: Mapped[str] = mapped_column(String(50), nullable=False)
    entidad_id: Mapped[str] = mapped_column(String(50), nullable=False)
    valor_anterior: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    valor_nuevo: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    patio_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
