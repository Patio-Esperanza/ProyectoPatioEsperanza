import uuid

from pydantic import BaseModel, model_validator

from app.models.enums import TipoMovimiento


class MovimientoCreate(BaseModel):
    contenedor_id: uuid.UUID
    ubicacion_destino_id: uuid.UUID
    tipo: TipoMovimiento
    override_manual: bool = False
    motivo_override: str | None = None
    score_sugerido: float | None = None
    score_elegido: float | None = None


class MovimientoOut(BaseModel):
    id: uuid.UUID
    contenedor_id: uuid.UUID
    ubicacion_destino_id: uuid.UUID | None
    tipo: TipoMovimiento


class SugerenciaUbicacionRequest(BaseModel):
    patio_id: uuid.UUID
    contenedor_id: uuid.UUID | None = None
    numero_contenedor: str | None = None
    punto_referencia_ubicacion_id: uuid.UUID | None = None
    punto_referencia_codigo: str | None = None

    @model_validator(mode="after")
    def _validar_identificadores(self) -> "SugerenciaUbicacionRequest":
        if self.contenedor_id is None and not self.numero_contenedor:
            raise ValueError("Se requiere contenedor_id o numero_contenedor")
        if self.punto_referencia_ubicacion_id is None and not self.punto_referencia_codigo:
            raise ValueError("Se requiere punto_referencia_ubicacion_id o punto_referencia_codigo")
        return self


class SugerenciaUbicacionResponse(BaseModel):
    ubicacion_id: uuid.UUID
    codigo: str
    costo: float
    tira_id: uuid.UUID
    nivel: int
