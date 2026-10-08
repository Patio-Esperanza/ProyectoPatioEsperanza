import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.core.iso6346 import validar_iso6346
from app.models.enums import EstadoContenedor, TamanoContenedor, TipoContenedor


def _numero_valido(value: str) -> str:
    value = value.strip().upper()
    if not validar_iso6346(value):
        raise ValueError("numero_contenedor no cumple el checksum ISO 6346")
    return value


class ContenedorCreate(BaseModel):
    numero_contenedor: str
    tipo: TipoContenedor
    tamano: TamanoContenedor
    patio_id: uuid.UUID
    peso_kg: int

    @field_validator("numero_contenedor")
    @classmethod
    def numero_valido(cls, value: str) -> str:
        return _numero_valido(value)


class ContenedorSolicitud(BaseModel):
    numero_contenedor: str
    tipo: TipoContenedor
    tamano: TamanoContenedor
    peso_kg: int
    fecha_estimada_retiro: datetime.datetime | None = None

    @field_validator("numero_contenedor")
    @classmethod
    def numero_valido(cls, value: str) -> str:
        return _numero_valido(value)


class ContenedorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    numero_contenedor: str
    tipo: TipoContenedor
    tamano: TamanoContenedor
    patio_id: uuid.UUID
    estado: EstadoContenedor
    peso_kg: int
    fecha_estimada_retiro: datetime.datetime | None = Field(
        default=None, validation_alias="fecha_estimada_salida"
    )
    fecha_deseada_salida: datetime.datetime | None = None
    pin_confirmacion: str | None = Field(default=None, exclude=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pin_pendiente(self) -> bool:
        return self.estado == EstadoContenedor.SOLICITUD_INGRESO and self.pin_confirmacion is not None


class PinOut(BaseModel):
    pin_confirmacion: str


class PinVerificar(BaseModel):
    numero_contenedor: str
    pin: str = Field(min_length=4, max_length=4)

    @field_validator("numero_contenedor")
    @classmethod
    def numero_valido(cls, value: str) -> str:
        return _numero_valido(value)

    @field_validator("pin")
    @classmethod
    def pin_valido(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("pin debe ser 4 dígitos")
        return value


class SolicitudSalida(BaseModel):
    fecha_deseada_salida: datetime.datetime
