import uuid
from sqlalchemy import Integer, ForeignKey, UniqueConstraint, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class Tira(Base):
    __tablename__ = "tiras"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tramo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tramos.id"), nullable=False)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_niveles: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=5)

    __table_args__ = (UniqueConstraint("tramo_id", "codigo", name="uq_tira_tramo_codigo"),)
