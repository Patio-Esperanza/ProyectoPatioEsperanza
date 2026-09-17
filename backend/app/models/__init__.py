"""Importa todos los modelos para que Base.metadata los conozca (usado por Alembic)."""

from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion  # noqa: F401
