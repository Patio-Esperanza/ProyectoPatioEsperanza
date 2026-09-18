import uuid

from pydantic import BaseModel

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
