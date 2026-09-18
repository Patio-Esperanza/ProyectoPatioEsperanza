from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import auth, contenedores, movimientos, patios, ubicaciones
from app.db import get_db

app = FastAPI(title="Patio Esperanza API")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health/db")
async def health_db(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(patios.router, prefix="/api/patios", tags=["patios"])
app.include_router(contenedores.router, prefix="/api/contenedores", tags=["contenedores"])
app.include_router(movimientos.router, prefix="/api/movimientos", tags=["movimientos"])
app.include_router(ubicaciones.router, prefix="/api/ubicaciones", tags=["ubicaciones"])
