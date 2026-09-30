import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class ReporteProgramado(Base):
    __tablename__ = "reportes_programados"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    tipo_reporte: Mapped[str] = mapped_column(String(50), nullable=False)
    patio_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("patios.id"), nullable=True)
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=True)
    frecuencia: Mapped[str] = mapped_column(String(20), nullable=False)
    hora: Mapped[int] = mapped_column(Integer, nullable=False)
    minuto: Mapped[int] = mapped_column(Integer, nullable=False)
    dia_semana: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dia_mes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    destinatarios: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    asunto: Mapped[str] = mapped_column(String(255), nullable=False)
    mensaje: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ultimo_envio: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ultimo_estado: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ultimo_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
