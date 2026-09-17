import uuid

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import TipoCliente


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    rfc: Mapped[str] = mapped_column(String(13), nullable=False, unique=True)
    tipo: Mapped[TipoCliente] = mapped_column(
        Enum(
            TipoCliente,
            name="tipo_cliente",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
