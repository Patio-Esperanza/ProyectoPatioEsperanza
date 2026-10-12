import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from app.core.iso6346 import validar_iso6346
from app.core.sellos import mostrar_sellos, normalizar_sellos
from app.models.enums import EstadoContenedor, TamanoContenedor, TipoContenedor


def _numero_valido(value: str) -> str:
    value = value.strip().upper()
    if not validar_iso6346(value):
        raise ValueError("numero_contenedor no cumple el checksum ISO 6346")
    return value


def _exigir_sello_si_lleno(tipo: TipoContenedor, sellos: str | None) -> None:
    # Un contenedor lleno debe traer sello: es la única garantía de que no se
    # abrió en tránsito. Marcarlo "sin sello" es una decisión explícita del
    # cliente (la casilla del formulario), no un campo que se pueda dejar vacío.
    if tipo == TipoContenedor.LLENO and sellos is None:
        raise ValueError("Un contenedor lleno requiere sello; si no tiene, márcalo sin sello")


class ContenedorCreate(BaseModel):
    numero_contenedor: str
    tipo: TipoContenedor
    tamano: TamanoContenedor
    patio_id: uuid.UUID
    peso_kg: int
    # Opcional aquí: el staff registra contenedores que todavía no pasan por
    # portería, y el sello se captura cuando llega la unidad. La exigencia para
    # contenedores llenos vive en `ContenedorSolicitud`, que es el formulario
    # de solicitud de entrada que llena el cliente.
    sellos: str | None = None

    @field_validator("numero_contenedor")
    @classmethod
    def numero_valido(cls, value: str) -> str:
        return _numero_valido(value)

    @field_validator("sellos")
    @classmethod
    def sellos_normalizados(cls, value: str | None) -> str | None:
        return normalizar_sellos(value)


class ContenedorSolicitud(BaseModel):
    numero_contenedor: str
    tipo: TipoContenedor
    tamano: TamanoContenedor
    peso_kg: int
    fecha_estimada_retiro: datetime.datetime | None = None
    sellos: str | None = None
    # No se guarda. Confirma que el cliente revisó y el contenedor no trae
    # sello, para distinguirlo de un campo que se olvidó llenar.
    sin_sello: bool = False

    @field_validator("numero_contenedor")
    @classmethod
    def numero_valido(cls, value: str) -> str:
        return _numero_valido(value)

    @field_validator("sellos")
    @classmethod
    def sellos_normalizados(cls, value: str | None) -> str | None:
        return normalizar_sellos(value)

    @model_validator(mode="after")
    def sello_obligatorio_si_lleno(self) -> "ContenedorSolicitud":
        if not self.sin_sello:
            _exigir_sello_si_lleno(self.tipo, self.sellos)
        return self


class ContenedorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    numero_contenedor: str
    tipo: TipoContenedor
    tamano: TamanoContenedor
    patio_id: uuid.UUID
    estado: EstadoContenedor
    peso_kg: int
    sellos: str | None = None
    fecha_estimada_retiro: datetime.datetime | None = Field(
        default=None, validation_alias="fecha_estimada_salida"
    )
    fecha_deseada_salida: datetime.datetime | None = None
    pin_confirmacion: str | None = Field(default=None, exclude=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pin_pendiente(self) -> bool:
        return self.estado == EstadoContenedor.SOLICITUD_INGRESO and self.pin_confirmacion is not None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sellos_texto(self) -> str:
        """Sello listo para mostrar. La leyenda vive aquí, no en cada pantalla."""
        return mostrar_sellos(self.sellos)


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
