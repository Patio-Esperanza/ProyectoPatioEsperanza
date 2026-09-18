# Fundación Backend — Patio Esperanza — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Levantar el backend FastAPI del sistema de patio: repo, esquema PostgreSQL (jerarquía de ubicación, clientes/usuarios, contenedores/movimientos, auditoría append-only), auth JWT + RBAC, algoritmo de sugerencia de ubicación, y aislamiento multi-patio por RLS.

**Architecture:** FastAPI (async) + SQLAlchemy 2.0 (async, asyncpg) + Alembic + PostgreSQL 16. Un rol de conexión restringido (`patio_app`) ejecuta la app; un rol propietario (`patio`, local) ejecuta migraciones — así la tabla de auditoría queda protegida contra UPDATE/DELETE incluso desde la app. RLS por `patio_id` vía variables de sesión (`SET LOCAL app.rol`, `SET LOCAL app.patios_asignados`) inyectadas por request.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async + asyncpg, Alembic, Pydantic v2 (`pydantic-settings`), PyJWT, passlib[bcrypt], pytest + pytest-asyncio + httpx, PostgreSQL 16 (docker-compose local).

**Fuera de alcance de este plan** (planes futuros, ver spec artifact sección 10): QR firmado/portería, portal cliente, PWA offline, mapa SVG, SSO/identidades federadas, API socios (Kasu/Loginco), deploy a DigitalOcean (`app.yaml` ya existe en el repo, se usa cuando corresponda).

## Global Constraints

- Multi-tenant: columna `patio_id` en toda tabla operativa + Postgres RLS. Un solo esquema — nunca esquema-por-patio (spec sección 3).
- `ubicaciones.nivel` entre 1 y 5. Prohibido apilar sin base (nivel N requiere nivel N-1 ocupado). Prohibido sobrescribir slot ocupado (bloqueo estricto).
- `auditoria` es append-only: el rol `patio_app` (usado por la app en runtime) nunca tiene UPDATE/DELETE sobre esa tabla.
- Sin PostGIS en esta fase.
- Zona horaria de negocio: `America/Mexico_City` (los timestamps se guardan en UTC, `TZ` es solo para presentación/jobs).
- Identidad: JWT propio ahora; el modelo debe dejar espacio para SSO futuro sin refactor — no se implementa SSO en este plan, pero ningún nombre de tabla/campo debe asumir que password es el único método de auth (`password_hash` ya es nullable).
- PostgreSQL 16, coincide con `databases: [{engine: PG, version: "16", name: cy-db}]` de `app.yaml`.
- Todas las pruebas corren contra Postgres real (no SQLite) — el esquema usa ENUM, ARRAY, JSONB, índices parciales y RLS, no portables a SQLite.

---

## File Structure

```
patio-esperanza/                       (raíz del repo, ya contiene app.yaml, CLAUDE.md, img/)
├── docker-compose.yml                 # Postgres local (dev + test)
├── docker/initdb/01-create-test-db.sql
├── .gitignore
└── backend/
    ├── requirements.txt
    ├── alembic.ini
    ├── pytest.ini
    ├── .env.example
    ├── app/
    │   ├── __init__.py
    │   ├── main.py                    # instancia FastAPI, routers, /api/health
    │   ├── config.py                  # Settings (pydantic-settings)
    │   ├── db.py                      # engine/session async, Base, get_db
    │   ├── alembic/
    │   │   ├── env.py
    │   │   └── versions/
    │   │       ├── 0001_baseline.py
    │   │       ├── 0002_ubicacion_jerarquia.py
    │   │       ├── 0003_cliente_usuario.py
    │   │       ├── 0004_auditoria_rol_app.py
    │   │       ├── 0005_contenedor_movimiento.py
    │   │       └── 0006_rls_policies.py
    │   ├── models/
    │   │   ├── __init__.py            # agrega todos los modelos a Base.metadata
    │   │   ├── enums.py               # TipoContenedor, TamanoContenedor, RolUsuario, TipoCliente, EstadoContenedor, TipoMovimiento
    │   │   ├── ubicacion.py           # Patio, Carril, Tramo, Tira, Ubicacion
    │   │   ├── cliente.py             # Cliente
    │   │   ├── usuario.py             # Usuario, UsuarioPatio
    │   │   ├── auditoria.py           # Auditoria
    │   │   └── contenedor.py          # Contenedor, Movimiento
    │   ├── schemas/
    │   │   ├── __init__.py
    │   │   ├── auth.py
    │   │   ├── patio.py
    │   │   ├── contenedor.py
    │   │   └── ubicacion.py
    │   ├── core/
    │   │   ├── __init__.py
    │   │   ├── security.py            # hash_password, verify_password, create_access_token, decode_access_token
    │   │   ├── auditoria.py           # registrar_auditoria()
    │   │   └── iso6346.py             # validar_iso6346()
    │   ├── services/
    │   │   ├── __init__.py
    │   │   └── ubicacion_algoritmo.py # scoring + sugerir_ubicacion()
    │   └── api/
    │       ├── __init__.py
    │       ├── deps.py                # get_current_user, require_roles, get_scoped_db
    │       └── routes/
    │           ├── __init__.py
    │           ├── auth.py
    │           ├── patios.py
    │           ├── contenedores.py
    │           ├── movimientos.py
    │           └── ubicaciones.py
    └── tests/
        ├── conftest.py
        ├── test_health.py
        ├── test_ubicacion_models.py
        ├── test_usuario_models.py
        ├── test_auditoria.py
        ├── test_contenedor_models.py
        ├── test_security.py
        ├── test_auth.py
        ├── test_patios_api.py
        ├── test_contenedores_api.py
        ├── test_movimientos_api.py
        ├── test_ubicacion_algoritmo.py
        └── test_rls.py
```

---

### Task 1: Repo + scaffold FastAPI + health check

**Files:**
- Create: `.gitignore`
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/pytest.ini`
- Create: `backend/tests/__init__.py`
- Test: `backend/tests/test_health.py`

**Interfaces:**
- Produces: `app.main.app` (instancia `FastAPI`), `GET /api/health` → `{"status": "ok"}`

- [ ] **Step 1: Inicializar repo git**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git init
```

- [ ] **Step 2: `.gitignore`**

```
__pycache__/
*.pyc
.venv/
venv/
.env
.pytest_cache/
node_modules/
.next/
*.egg-info/
```

- [ ] **Step 3: `backend/requirements.txt`**

```
fastapi==0.115.6
uvicorn[standard]==0.32.1
sqlalchemy==2.0.36
asyncpg==0.30.0
alembic==1.14.0
pydantic==2.10.3
pydantic-settings==2.6.1
pyjwt==2.10.1
passlib[bcrypt]==1.7.4
python-multipart==0.0.19
pytest==8.3.4
pytest-asyncio==0.24.0
httpx==0.28.1
```

- [ ] **Step 4: Crear entorno e instalar**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 5: `backend/pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 6: Escribir test que falla**

`backend/tests/__init__.py` (vacío) y `backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 7: Correr test, confirmar que falla**

```bash
cd backend && pytest tests/test_health.py -v
```
Esperado: FAIL — `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 8: `backend/app/__init__.py`** (vacío) y **`backend/app/main.py`**

```python
from fastapi import FastAPI

app = FastAPI(title="Patio Esperanza API")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 9: Correr test, confirmar que pasa**

```bash
cd backend && pytest tests/test_health.py -v
```
Esperado: PASS

- [ ] **Step 10: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add .gitignore backend/requirements.txt backend/pytest.ini backend/app backend/tests
git commit -m "feat: scaffold FastAPI backend con health check"
```

---

### Task 2: Postgres local + engine async + Alembic + `/api/health/db`

**Files:**
- Create: `docker-compose.yml`
- Create: `docker/initdb/01-create-test-db.sql`
- Create: `backend/.env.example`
- Create: `backend/app/config.py`
- Create: `backend/app/db.py`
- Create: `backend/alembic.ini`
- Create: `backend/app/alembic/env.py`
- Create: `backend/app/alembic/versions/0001_baseline.py`
- Create: `backend/app/models/__init__.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/conftest.py`
- Test: `backend/tests/test_health.py` (agrega caso `/api/health/db`)

**Interfaces:**
- Consumes: `app.main.app` (Task 1)
- Produces: `app.config.settings`, `app.db.Base`, `app.db.get_db`, fixtures `apply_migrations`, `db_session`, `client` en `conftest.py` (usadas por todos los tasks siguientes)

- [ ] **Step 1: `docker-compose.yml`** (raíz del repo)

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: patio
      POSTGRES_PASSWORD: patio
      POSTGRES_DB: patio_dev
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./docker/initdb:/docker-entrypoint-initdb.d
volumes:
  pgdata:
```

- [ ] **Step 2: `docker/initdb/01-create-test-db.sql`**

```sql
CREATE DATABASE patio_test;
```

- [ ] **Step 3: Levantar Postgres**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
docker compose up -d db
```
Esperado: contenedor `db` healthy, puerto 5432 escuchando.

- [ ] **Step 4: `backend/.env.example`**

```
DATABASE_URL=postgresql+asyncpg://patio_app:patio_app@localhost:5432/patio_dev
MIGRATIONS_DATABASE_URL=postgresql+asyncpg://patio:patio@localhost:5432/patio_dev
JWT_SECRET=dev-secret-change-me
JWT_EXPIRES_MINUTES=60
```

- [ ] **Step 5: `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    migrations_database_url: str
    jwt_secret: str
    jwt_expires_minutes: int = 60


settings = Settings()
```

- [ ] **Step 6: `backend/app/db.py`**

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db():
    async with SessionLocal() as session:
        yield session
```

- [ ] **Step 7: `backend/app/models/__init__.py`**

```python
"""Importa todos los modelos para que Base.metadata los conozca (usado por Alembic)."""
```

- [ ] **Step 8: `backend/alembic.ini`**

```ini
[alembic]
script_location = app/alembic

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

- [ ] **Step 9: `backend/app/alembic/env.py`**

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.db import Base
import app.models  # noqa: F401  registra modelos en Base.metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return settings.migrations_database_url


def run_migrations_offline() -> None:
    context.configure(url=get_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        {"sqlalchemy.url": get_url()},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 10: `backend/app/alembic/versions/0001_baseline.py`**

```python
"""baseline

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-14
"""
revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
```

- [ ] **Step 11: Agregar `/api/health/db` en `backend/app/main.py`**

```python
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db

app = FastAPI(title="Patio Esperanza API")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health/db")
async def health_db(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}
```

- [ ] **Step 12: `backend/tests/conftest.py`**

```python
import os
import subprocess
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://patio_app:patio_app@localhost:5432/patio_test"
)
os.environ.setdefault(
    "MIGRATIONS_DATABASE_URL", "postgresql+asyncpg://patio:patio@localhost:5432/patio_test"
)
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_EXPIRES_MINUTES", "60")

from app.db import get_db  # noqa: E402
from app.main import app  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def apply_migrations():
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        check=True,
    )
    yield


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(os.environ["DATABASE_URL"])
    connection = await engine.connect()
    trans = await connection.begin()
    session_factory = async_sessionmaker(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
        class_=AsyncSession,
    )
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await connection.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    async def _get_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

- [ ] **Step 13: Crear rol `patio_app` (mínimo, ampliado en Task 5) y exportar env vars de prueba**

```bash
docker exec -it $(docker compose ps -q db) psql -U patio -d patio_dev -c \
  "CREATE ROLE patio_app LOGIN PASSWORD 'patio_app';"
docker exec -it $(docker compose ps -q db) psql -U patio -d patio_test -c \
  "GRANT CONNECT ON DATABASE patio_test TO patio_app;"
docker exec -it $(docker compose ps -q db) psql -U patio -d patio_dev -c \
  "GRANT CONNECT ON DATABASE patio_dev TO patio_app;"
```
Nota: la creación de rol es cluster-wide (una sola vez alcanza para ambas DBs); los GRANT son por base.

- [ ] **Step 14: Agregar caso a `backend/tests/test_health.py`**

```python
import pytest


@pytest.mark.anyio
async def test_health_db_returns_connected(client):
    response = await client.get("/api/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "connected"}
```

Reemplazar el test síncrono existente (`test_health_returns_ok`) por su versión async usando el fixture `client`:

```python
import pytest


@pytest.mark.anyio
async def test_health_returns_ok(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_health_db_returns_connected(client):
    response = await client.get("/api/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "connected"}
```

- [ ] **Step 15: Correr tests, confirmar que pasan**

```bash
cd backend && pytest tests/test_health.py -v
```
Esperado: PASS (2 tests). `apply_migrations` corre `alembic upgrade head` contra `patio_test` como parte del setup de sesión.

- [ ] **Step 16: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add docker-compose.yml docker/initdb backend/.env.example backend/app/config.py \
  backend/app/db.py backend/app/models backend/alembic.ini backend/app/alembic \
  backend/app/main.py backend/tests/conftest.py backend/tests/test_health.py
git commit -m "feat: engine async, Alembic, health check contra DB real"
```

---

### Task 3: Jerarquía de ubicación (Patio, Carril, Tramo, Tira, Ubicación)

**Files:**
- Create: `backend/app/models/enums.py`
- Create: `backend/app/models/ubicacion.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/alembic/versions/0002_ubicacion_jerarquia.py`
- Test: `backend/tests/test_ubicacion_models.py`

**Interfaces:**
- Produces: `TipoContenedor` (enum: `LLENO`, `VACIO`), modelos `Patio`, `Carril` (con `tipo_teorico: TipoContenedor | None`), `Tramo`, `Tira`, `Ubicacion` (con `nivel: int`, check 1–5)
- Consumes: `app.db.Base` (Task 2)

- [ ] **Step 1: Escribir test que falla**

`backend/tests/test_ubicacion_models.py`:

```python
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.enums import TipoContenedor
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion


@pytest.mark.anyio
async def test_crea_jerarquia_completa(db_session):
    patio = Patio(nombre="Patio Norte", codigo="PN")
    db_session.add(patio)
    await db_session.flush()

    carril = Carril(patio_id=patio.id, codigo="A1", orden=0, tipo_teorico=TipoContenedor.LLENO)
    db_session.add(carril)
    await db_session.flush()

    tramo = Tramo(carril_id=carril.id, codigo="T1", orden=0)
    db_session.add(tramo)
    await db_session.flush()

    tira = Tira(tramo_id=tramo.id, codigo="S1", orden=0)
    db_session.add(tira)
    await db_session.flush()

    ubicacion = Ubicacion(tira_id=tira.id, nivel=1, codigo="A1-T1-S1-N1")
    db_session.add(ubicacion)
    await db_session.flush()

    result = await db_session.execute(select(Ubicacion).where(Ubicacion.id == ubicacion.id))
    assert result.scalar_one().nivel == 1


@pytest.mark.anyio
async def test_nivel_fuera_de_rango_falla(db_session):
    patio = Patio(nombre="Patio Norte", codigo="PN2")
    db_session.add(patio)
    await db_session.flush()
    carril = Carril(patio_id=patio.id, codigo="A1", orden=0)
    db_session.add(carril)
    await db_session.flush()
    tramo = Tramo(carril_id=carril.id, codigo="T1", orden=0)
    db_session.add(tramo)
    await db_session.flush()
    tira = Tira(tramo_id=tramo.id, codigo="S1", orden=0)
    db_session.add(tira)
    await db_session.flush()

    db_session.add(Ubicacion(tira_id=tira.id, nivel=6, codigo="bad"))
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.anyio
async def test_no_duplica_slot_tira_nivel(db_session):
    patio = Patio(nombre="Patio Norte", codigo="PN3")
    db_session.add(patio)
    await db_session.flush()
    carril = Carril(patio_id=patio.id, codigo="A1", orden=0)
    db_session.add(carril)
    await db_session.flush()
    tramo = Tramo(carril_id=carril.id, codigo="T1", orden=0)
    db_session.add(tramo)
    await db_session.flush()
    tira = Tira(tramo_id=tramo.id, codigo="S1", orden=0)
    db_session.add(tira)
    await db_session.flush()

    db_session.add(Ubicacion(tira_id=tira.id, nivel=1, codigo="dup-1"))
    await db_session.flush()
    db_session.add(Ubicacion(tira_id=tira.id, nivel=1, codigo="dup-2"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd backend && pytest tests/test_ubicacion_models.py -v
```
Esperado: FAIL — `ModuleNotFoundError: No module named 'app.models.ubicacion'`

- [ ] **Step 3: `backend/app/models/enums.py`**

```python
import enum


class TipoContenedor(str, enum.Enum):
    LLENO = "lleno"
    VACIO = "vacio"
```

- [ ] **Step 4: `backend/app/models/ubicacion.py`**

```python
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import TipoContenedor


class Patio(Base):
    __tablename__ = "patios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="America/Mexico_City")
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Carril(Base):
    __tablename__ = "carriles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patios.id"), nullable=False)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tipo_teorico: Mapped[TipoContenedor | None] = mapped_column(
        Enum(TipoContenedor, name="tipo_contenedor"), nullable=True
    )

    __table_args__ = (UniqueConstraint("patio_id", "codigo", name="uq_carril_patio_codigo"),)


class Tramo(Base):
    __tablename__ = "tramos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    carril_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("carriles.id"), nullable=False)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (UniqueConstraint("carril_id", "codigo", name="uq_tramo_carril_codigo"),)


class Tira(Base):
    __tablename__ = "tiras"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tramo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tramos.id"), nullable=False)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (UniqueConstraint("tramo_id", "codigo", name="uq_tira_tramo_codigo"),)


class Ubicacion(Base):
    __tablename__ = "ubicaciones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tira_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tiras.id"), nullable=False)
    nivel: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    capacidad_peso_kg: Mapped[int] = mapped_column(Integer, nullable=False, default=30000)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("tira_id", "nivel", name="uq_ubicacion_tira_nivel"),
        CheckConstraint("nivel BETWEEN 1 AND 5", name="ck_ubicacion_nivel_1_5"),
    )
```

- [ ] **Step 5: Registrar en `backend/app/models/__init__.py`**

```python
"""Importa todos los modelos para que Base.metadata los conozca (usado por Alembic)."""

from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion  # noqa: F401
```

- [ ] **Step 6: `backend/app/alembic/versions/0002_ubicacion_jerarquia.py`**

```python
"""ubicacion jerarquia

Revision ID: 0002_ubicacion_jerarquia
Revises: 0001_baseline
Create Date: 2026-09-14
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_ubicacion_jerarquia"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

tipo_contenedor = postgresql.ENUM("lleno", "vacio", name="tipo_contenedor")


def upgrade() -> None:
    tipo_contenedor.create(op.get_bind())

    op.create_table(
        "patios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False, unique=True),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="America/Mexico_City"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "carriles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patios.id"), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tipo_teorico", tipo_contenedor, nullable=True),
        sa.UniqueConstraint("patio_id", "codigo", name="uq_carril_patio_codigo"),
    )
    op.create_table(
        "tramos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("carril_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("carriles.id"), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("carril_id", "codigo", name="uq_tramo_carril_codigo"),
    )
    op.create_table(
        "tiras",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tramo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tramos.id"), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("tramo_id", "codigo", name="uq_tira_tramo_codigo"),
    )
    op.create_table(
        "ubicaciones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tira_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tiras.id"), nullable=False),
        sa.Column("nivel", sa.SmallInteger(), nullable=False),
        sa.Column("codigo", sa.String(30), nullable=False),
        sa.Column("capacidad_peso_kg", sa.Integer(), nullable=False, server_default="30000"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("tira_id", "nivel", name="uq_ubicacion_tira_nivel"),
        sa.CheckConstraint("nivel BETWEEN 1 AND 5", name="ck_ubicacion_nivel_1_5"),
    )


def downgrade() -> None:
    op.drop_table("ubicaciones")
    op.drop_table("tiras")
    op.drop_table("tramos")
    op.drop_table("carriles")
    op.drop_table("patios")
    tipo_contenedor.drop(op.get_bind())
```

- [ ] **Step 7: Correr tests, confirmar que pasan**

```bash
cd backend && pytest tests/test_ubicacion_models.py -v
```
Esperado: PASS (3 tests)

- [ ] **Step 8: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/models backend/app/alembic/versions/0002_ubicacion_jerarquia.py \
  backend/tests/test_ubicacion_models.py
git commit -m "feat: jerarquia PATIO-CARRIL-TRAMO-TIRA-NIVEL con constraints"
```

---

### Task 4: Cliente, Usuario, UsuarioPatio + roles

**Files:**
- Modify: `backend/app/models/enums.py`
- Create: `backend/app/models/cliente.py`
- Create: `backend/app/models/usuario.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/alembic/versions/0003_cliente_usuario.py`
- Test: `backend/tests/test_usuario_models.py`

**Interfaces:**
- Produces: `RolUsuario` (enum: `CLIENTE`, `OPERADOR`, `SUPERVISOR`, `ADMIN`, `GUARDIA`, `DESPACHADOR`), `TipoCliente` (enum: `AGENCIA_ADUANAL`, `IMPORTADOR_EXPORTADOR`, `TRANSPORTISTA`, `SOCIO_API`), modelos `Cliente`, `Usuario` (`password_hash: str | None`), `UsuarioPatio`
- Consumes: `Patio` (Task 3)

- [ ] **Step 1: Escribir test que falla**

`backend/tests/test_usuario_models.py`:

```python
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.cliente import Cliente
from app.models.enums import RolUsuario, TipoCliente
from app.models.ubicacion import Patio
from app.models.usuario import Usuario, UsuarioPatio


@pytest.mark.anyio
async def test_crea_usuario_interno_con_patio_asignado(db_session):
    patio = Patio(nombre="Patio Norte", codigo="PN")
    db_session.add(patio)
    await db_session.flush()

    usuario = Usuario(
        tipo=RolUsuario.OPERADOR,
        email="operador@patio.mx",
        password_hash="hash",
        activo=True,
    )
    db_session.add(usuario)
    await db_session.flush()

    db_session.add(UsuarioPatio(usuario_id=usuario.id, patio_id=patio.id))
    await db_session.flush()

    result = await db_session.execute(select(Usuario).where(Usuario.id == usuario.id))
    assert result.scalar_one().tipo == RolUsuario.OPERADOR


@pytest.mark.anyio
async def test_crea_usuario_cliente_ligado_a_cliente(db_session):
    cliente = Cliente(
        razon_social="Agencia Aduanal Ejemplo SA de CV",
        rfc="AAE010101AA1",
        tipo=TipoCliente.AGENCIA_ADUANAL,
    )
    db_session.add(cliente)
    await db_session.flush()

    usuario = Usuario(
        tipo=RolUsuario.CLIENTE,
        cliente_id=cliente.id,
        email="contacto@agencia.mx",
        password_hash="hash",
        activo=True,
    )
    db_session.add(usuario)
    await db_session.flush()
    assert usuario.cliente_id == cliente.id


@pytest.mark.anyio
async def test_email_duplicado_falla(db_session):
    db_session.add(Usuario(tipo=RolUsuario.ADMIN, email="dup@patio.mx", password_hash="h", activo=True))
    await db_session.flush()
    db_session.add(Usuario(tipo=RolUsuario.ADMIN, email="dup@patio.mx", password_hash="h", activo=True))
    with pytest.raises(IntegrityError):
        await db_session.flush()
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd backend && pytest tests/test_usuario_models.py -v
```
Esperado: FAIL — `ModuleNotFoundError: No module named 'app.models.cliente'`

- [ ] **Step 3: Agregar enums en `backend/app/models/enums.py`**

```python
import enum


class TipoContenedor(str, enum.Enum):
    LLENO = "lleno"
    VACIO = "vacio"


class RolUsuario(str, enum.Enum):
    CLIENTE = "cliente"
    OPERADOR = "operador"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"
    GUARDIA = "guardia"
    DESPACHADOR = "despachador"


class TipoCliente(str, enum.Enum):
    AGENCIA_ADUANAL = "agencia_aduanal"
    IMPORTADOR_EXPORTADOR = "importador_exportador"
    TRANSPORTISTA = "transportista"
    SOCIO_API = "socio_api"
```

- [ ] **Step 4: `backend/app/models/cliente.py`**

```python
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
    tipo: Mapped[TipoCliente] = mapped_column(Enum(TipoCliente, name="tipo_cliente"), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
```

- [ ] **Step 5: `backend/app/models/usuario.py`**

```python
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import RolUsuario


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=True
    )
    tipo: Mapped[RolUsuario] = mapped_column(Enum(RolUsuario, name="rol_usuario"), nullable=False)
    nombre: Mapped[str | None] = mapped_column(String(150), nullable=True)
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mfa_habilitado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class UsuarioPatio(Base):
    __tablename__ = "usuario_patio"

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), primary_key=True
    )
    patio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patios.id"), primary_key=True
    )
```

- [ ] **Step 6: Registrar en `backend/app/models/__init__.py`**

```python
"""Importa todos los modelos para que Base.metadata los conozca (usado por Alembic)."""

from app.models.cliente import Cliente  # noqa: F401
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion  # noqa: F401
from app.models.usuario import Usuario, UsuarioPatio  # noqa: F401
```

- [ ] **Step 7: `backend/app/alembic/versions/0003_cliente_usuario.py`**

```python
"""cliente usuario

Revision ID: 0003_cliente_usuario
Revises: 0002_ubicacion_jerarquia
Create Date: 2026-09-14
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_cliente_usuario"
down_revision = "0002_ubicacion_jerarquia"
branch_labels = None
depends_on = None

tipo_cliente = postgresql.ENUM("agencia_aduanal", "importador_exportador", "transportista", "socio_api", name="tipo_cliente")
rol_usuario = postgresql.ENUM("cliente", "operador", "supervisor", "admin", "guardia", "despachador", name="rol_usuario")


def upgrade() -> None:
    tipo_cliente.create(op.get_bind())
    rol_usuario.create(op.get_bind())

    op.create_table(
        "clientes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("razon_social", sa.String(200), nullable=False),
        sa.Column("rfc", sa.String(13), nullable=False, unique=True),
        sa.Column("tipo", tipo_cliente, nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "usuarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clientes.id"), nullable=True),
        sa.Column("tipo", rol_usuario, nullable=False),
        sa.Column("nombre", sa.String(150), nullable=True),
        sa.Column("email", sa.String(200), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("mfa_habilitado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "usuario_patio",
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), primary_key=True),
        sa.Column("patio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patios.id"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("usuario_patio")
    op.drop_table("usuarios")
    op.drop_table("clientes")
    rol_usuario.drop(op.get_bind())
    tipo_cliente.drop(op.get_bind())
```

- [ ] **Step 8: Correr tests, confirmar que pasan**

```bash
cd backend && pytest tests/test_usuario_models.py -v
```
Esperado: PASS (3 tests)

- [ ] **Step 9: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/models backend/app/alembic/versions/0003_cliente_usuario.py \
  backend/tests/test_usuario_models.py
git commit -m "feat: modelos Cliente, Usuario, UsuarioPatio con RBAC base"
```

---

### Task 5: Auditoría append-only + rol `patio_app` restringido

**Files:**
- Create: `backend/app/models/auditoria.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/auditoria.py`
- Create: `backend/app/alembic/versions/0004_auditoria_rol_app.py`
- Test: `backend/tests/test_auditoria.py`

**Interfaces:**
- Produces: modelo `Auditoria`, función `registrar_auditoria(db, *, usuario_id, rol, ip, dispositivo, accion, entidad, entidad_id, valor_anterior, valor_nuevo, patio_id) -> None` (usada por Tasks 8–11)
- Consumes: nada nuevo de tasks previos más allá de `Base`

- [ ] **Step 1: Escribir test que falla**

`backend/tests/test_auditoria.py`:

```python
import os

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.auditoria import registrar_auditoria
from app.models.auditoria import Auditoria
from app.models.enums import RolUsuario
from app.models.usuario import Usuario


@pytest.mark.anyio
async def test_registrar_auditoria_inserta_fila(db_session):
    usuario = Usuario(tipo=RolUsuario.ADMIN, email="audit@patio.mx", password_hash="h", activo=True)
    db_session.add(usuario)
    await db_session.flush()

    await registrar_auditoria(
        db_session,
        usuario_id=usuario.id,
        rol=RolUsuario.ADMIN.value,
        ip="127.0.0.1",
        dispositivo="pytest",
        accion="crear",
        entidad="usuarios",
        entidad_id=str(usuario.id),
        valor_anterior=None,
        valor_nuevo={"email": usuario.email},
        patio_id=None,
    )
    await db_session.flush()

    result = await db_session.execute(text("SELECT accion, entidad FROM auditoria"))
    row = result.one()
    assert row.accion == "crear"
    assert row.entidad == "usuarios"


@pytest.mark.anyio
async def test_rol_app_no_puede_update_ni_delete_auditoria(db_session):
    await db_session.execute(
        text(
            "INSERT INTO auditoria (id, ts, usuario_id, rol, ip, dispositivo, accion, entidad, entidad_id, "
            "valor_anterior, valor_nuevo, patio_id) VALUES "
            "(gen_random_uuid(), now(), NULL, 'admin', '127.0.0.1', 'pytest', 'crear', 'x', 'x', NULL, NULL, NULL)"
        )
    )
    await db_session.flush()

    app_engine = create_async_engine(os.environ["DATABASE_URL"])
    async with app_engine.connect() as conn:
        with pytest.raises(DBAPIError, match="permission denied"):
            await conn.execute(text("UPDATE auditoria SET accion = 'modificado'"))
    await app_engine.dispose()
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd backend && pytest tests/test_auditoria.py -v
```
Esperado: FAIL — `ModuleNotFoundError: No module named 'app.models.auditoria'`

- [ ] **Step 3: `backend/app/models/auditoria.py`**

```python
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
```

- [ ] **Step 4: `backend/app/core/__init__.py`** (vacío) y **`backend/app/core/auditoria.py`**

```python
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auditoria import Auditoria


async def registrar_auditoria(
    db: AsyncSession,
    *,
    usuario_id: uuid.UUID | None,
    rol: str,
    ip: str,
    dispositivo: str,
    accion: str,
    entidad: str,
    entidad_id: str,
    valor_anterior: dict[str, Any] | None,
    valor_nuevo: dict[str, Any] | None,
    patio_id: uuid.UUID | None,
) -> None:
    db.add(
        Auditoria(
            usuario_id=usuario_id,
            rol=rol,
            ip=ip,
            dispositivo=dispositivo,
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
            valor_anterior=valor_anterior,
            valor_nuevo=valor_nuevo,
            patio_id=patio_id,
        )
    )
```

- [ ] **Step 5: Registrar en `backend/app/models/__init__.py`**

```python
"""Importa todos los modelos para que Base.metadata los conozca (usado por Alembic)."""

from app.models.auditoria import Auditoria  # noqa: F401
from app.models.cliente import Cliente  # noqa: F401
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion  # noqa: F401
from app.models.usuario import Usuario, UsuarioPatio  # noqa: F401
```

- [ ] **Step 6: `backend/app/alembic/versions/0004_auditoria_rol_app.py`**

```python
"""auditoria + rol patio_app restringido

Revision ID: 0004_auditoria_rol_app
Revises: 0003_cliente_usuario
Create Date: 2026-09-14
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_auditoria_rol_app"
down_revision = "0003_cliente_usuario"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auditoria",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rol", sa.String(30), nullable=False),
        sa.Column("ip", sa.String(45), nullable=False),
        sa.Column("dispositivo", sa.String(200), nullable=False),
        sa.Column("accion", sa.String(50), nullable=False),
        sa.Column("entidad", sa.String(50), nullable=False),
        sa.Column("entidad_id", sa.String(50), nullable=False),
        sa.Column("valor_anterior", postgresql.JSONB(), nullable=True),
        sa.Column("valor_nuevo", postgresql.JSONB(), nullable=True),
        sa.Column("patio_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_auditoria_entidad", "auditoria", ["entidad", "entidad_id"])

    op.execute(
        """
        DO $$ BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'patio_app') THEN
            CREATE ROLE patio_app LOGIN PASSWORD 'patio_app';
          END IF;
        END $$;
        """
    )
    op.execute("GRANT CONNECT ON DATABASE " + op.get_bind().engine.url.database + " TO patio_app;")
    op.execute("GRANT USAGE ON SCHEMA public TO patio_app;")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO patio_app;")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO patio_app;")
    op.execute("REVOKE UPDATE, DELETE ON auditoria FROM patio_app;")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO patio_app;"
    )


def downgrade() -> None:
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM patio_app;")
    op.drop_index("ix_auditoria_entidad", table_name="auditoria")
    op.drop_table("auditoria")
```

- [ ] **Step 7: Correr tests, confirmar que pasan**

```bash
cd backend && pytest tests/test_auditoria.py -v
```
Esperado: PASS (2 tests). El segundo test conecta directo con el rol `patio_app` (vía `DATABASE_URL`) y confirma que Postgres rechaza el `UPDATE`.

- [ ] **Step 8: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/models/auditoria.py backend/app/models/__init__.py \
  backend/app/core backend/app/alembic/versions/0004_auditoria_rol_app.py \
  backend/tests/test_auditoria.py
git commit -m "feat: auditoria append-only, rol patio_app sin UPDATE/DELETE"
```

---

### Task 6: Contenedor + Movimiento (máquina de estados)

**Files:**
- Modify: `backend/app/models/enums.py`
- Create: `backend/app/models/contenedor.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/core/iso6346.py`
- Create: `backend/app/alembic/versions/0005_contenedor_movimiento.py`
- Test: `backend/tests/test_contenedor_models.py`

**Interfaces:**
- Produces: `EstadoContenedor` (enum, 12 estados de la máquina de estados — sección 2 del spec), `TamanoContenedor` (`VEINTE`, `CUARENTA`, `CUARENTA_Y_CINCO`), `TipoMovimiento` (`INGRESO`, `REUBICACION`, `SERVICIO`, `SALIDA`), modelos `Contenedor` (con `fecha_estimada_salida: datetime | None`, `patio_id`, `ubicacion_id` único parcial), `Movimiento` (con `patio_id` denormalizado para RLS), `validar_iso6346(numero: str) -> bool`
- Consumes: `Ubicacion`, `Cliente`, `Usuario`, `TipoContenedor` (Tasks 3–4)

- [ ] **Step 1: Escribir test que falla — checksum ISO 6346**

`backend/tests/test_contenedor_models.py`:

```python
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.iso6346 import validar_iso6346
from app.models.cliente import Cliente
from app.models.contenedor import Contenedor, Movimiento
from app.models.enums import EstadoContenedor, TamanoContenedor, TipoCliente, TipoContenedor, TipoMovimiento
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion


def test_validar_iso6346_numero_valido():
    assert validar_iso6346("CSQU3054383") is True


def test_validar_iso6346_digito_verificador_incorrecto():
    assert validar_iso6346("CSQU3054380") is False


def test_validar_iso6346_formato_invalido():
    assert validar_iso6346("ABC123") is False


@pytest.mark.anyio
async def test_crea_contenedor_y_lo_ubica(db_session):
    patio = Patio(nombre="Patio Norte", codigo="PN")
    db_session.add(patio)
    await db_session.flush()
    carril = Carril(patio_id=patio.id, codigo="A1", orden=0)
    db_session.add(carril)
    await db_session.flush()
    tramo = Tramo(carril_id=carril.id, codigo="T1", orden=0)
    db_session.add(tramo)
    await db_session.flush()
    tira = Tira(tramo_id=tramo.id, codigo="S1", orden=0)
    db_session.add(tira)
    await db_session.flush()
    ubicacion = Ubicacion(tira_id=tira.id, nivel=1, codigo="A1-T1-S1-N1")
    db_session.add(ubicacion)
    await db_session.flush()

    cliente = Cliente(razon_social="Importadora X", rfc="IMX010101AA1", tipo=TipoCliente.IMPORTADOR_EXPORTADOR)
    db_session.add(cliente)
    await db_session.flush()

    contenedor = Contenedor(
        numero_contenedor="CSQU3054383",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.CUARENTA,
        cliente_id=cliente.id,
        patio_id=patio.id,
        ubicacion_id=ubicacion.id,
        estado=EstadoContenedor.UBICADO,
        peso_kg=18000,
    )
    db_session.add(contenedor)
    await db_session.flush()

    db_session.add(
        Movimiento(
            contenedor_id=contenedor.id,
            patio_id=patio.id,
            tipo=TipoMovimiento.INGRESO,
            ubicacion_origen_id=None,
            ubicacion_destino_id=ubicacion.id,
            operador_id=None,
            override_manual=False,
        )
    )
    await db_session.flush()

    result = await db_session.execute(select(Contenedor).where(Contenedor.id == contenedor.id))
    assert result.scalar_one().estado == EstadoContenedor.UBICADO


@pytest.mark.anyio
async def test_no_permite_dos_contenedores_en_misma_ubicacion(db_session):
    patio = Patio(nombre="Patio Norte", codigo="PN2")
    db_session.add(patio)
    await db_session.flush()
    carril = Carril(patio_id=patio.id, codigo="A1", orden=0)
    db_session.add(carril)
    await db_session.flush()
    tramo = Tramo(carril_id=carril.id, codigo="T1", orden=0)
    db_session.add(tramo)
    await db_session.flush()
    tira = Tira(tramo_id=tramo.id, codigo="S1", orden=0)
    db_session.add(tira)
    await db_session.flush()
    ubicacion = Ubicacion(tira_id=tira.id, nivel=1, codigo="A1-T1-S1-N1")
    db_session.add(ubicacion)
    await db_session.flush()

    db_session.add(
        Contenedor(
            numero_contenedor="CSQU3054383",
            tipo=TipoContenedor.LLENO,
            tamano=TamanoContenedor.CUARENTA,
            patio_id=patio.id,
            ubicacion_id=ubicacion.id,
            estado=EstadoContenedor.UBICADO,
            peso_kg=18000,
        )
    )
    await db_session.flush()

    db_session.add(
        Contenedor(
            numero_contenedor="TRHU1866154",
            tipo=TipoContenedor.LLENO,
            tamano=TamanoContenedor.CUARENTA,
            patio_id=patio.id,
            ubicacion_id=ubicacion.id,
            estado=EstadoContenedor.UBICADO,
            peso_kg=15000,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd backend && pytest tests/test_contenedor_models.py -v
```
Esperado: FAIL — `ModuleNotFoundError: No module named 'app.core.iso6346'`

- [ ] **Step 3: `backend/app/core/iso6346.py`**

```python
_VALORES_LETRA = {
    "A": 10, "B": 12, "C": 13, "D": 14, "E": 15, "F": 16, "G": 17, "H": 18,
    "I": 19, "J": 20, "K": 21, "L": 23, "M": 24, "N": 25, "O": 26, "P": 27,
    "Q": 28, "R": 29, "S": 30, "T": 31, "U": 32, "V": 34, "W": 35, "X": 36,
    "Y": 37, "Z": 38,
}


def validar_iso6346(numero: str) -> bool:
    numero = numero.strip().upper()
    if len(numero) != 11:
        return False
    if not numero[:4].isalpha() or numero[3] not in "UJZ":
        return False
    if not numero[4:10].isdigit():
        return False
    if not numero[10].isdigit():
        return False

    total = 0
    for i, ch in enumerate(numero[:10]):
        valor = _VALORES_LETRA[ch] if ch.isalpha() else int(ch)
        total += valor * (2**i)

    digito_verificador = total % 11
    if digito_verificador == 10:
        digito_verificador = 0
    return digito_verificador == int(numero[10])
```

- [ ] **Step 4: Agregar enums en `backend/app/models/enums.py`**

```python
import enum


class TipoContenedor(str, enum.Enum):
    LLENO = "lleno"
    VACIO = "vacio"


class RolUsuario(str, enum.Enum):
    CLIENTE = "cliente"
    OPERADOR = "operador"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"
    GUARDIA = "guardia"
    DESPACHADOR = "despachador"


class TipoCliente(str, enum.Enum):
    AGENCIA_ADUANAL = "agencia_aduanal"
    IMPORTADOR_EXPORTADOR = "importador_exportador"
    TRANSPORTISTA = "transportista"
    SOCIO_API = "socio_api"


class TamanoContenedor(str, enum.Enum):
    VEINTE = "20"
    CUARENTA = "40"
    CUARENTA_Y_CINCO = "45"


class EstadoContenedor(str, enum.Enum):
    SOLICITUD_INGRESO = "solicitud_ingreso"
    QR_INGRESO_EMITIDO = "qr_ingreso_emitido"
    EN_PORTERIA = "en_porteria"
    INGRESADO = "ingresado"
    UBICADO = "ubicado"
    EN_ESTADIA = "en_estadia"
    EN_SERVICIO_ESPECIAL = "en_servicio_especial"
    SOLICITUD_SALIDA = "solicitud_salida"
    QR_SALIDA_EMITIDO = "qr_salida_emitido"
    EN_PORTERIA_SALIDA = "en_porteria_salida"
    DESPACHADO = "despachado"
    RECHAZADO = "rechazado"


class TipoMovimiento(str, enum.Enum):
    INGRESO = "ingreso"
    REUBICACION = "reubicacion"
    SERVICIO = "servicio"
    SALIDA = "salida"
```

- [ ] **Step 5: `backend/app/models/contenedor.py`**

```python
import datetime
import uuid

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base
from app.models.enums import EstadoContenedor, TamanoContenedor, TipoContenedor, TipoMovimiento


class Contenedor(Base):
    __tablename__ = "contenedores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero_contenedor: Mapped[str] = mapped_column(String(11), nullable=False)
    tipo: Mapped[TipoContenedor] = mapped_column(Enum(TipoContenedor, name="tipo_contenedor"), nullable=False)
    tamano: Mapped[TamanoContenedor] = mapped_column(
        Enum(TamanoContenedor, name="tamano_contenedor"), nullable=False
    )
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=True)
    patio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patios.id"), nullable=False)
    ubicacion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ubicaciones.id"), nullable=True
    )
    estado: Mapped[EstadoContenedor] = mapped_column(
        Enum(EstadoContenedor, name="estado_contenedor"), nullable=False
    )
    peso_kg: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_estimada_salida: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index(
            "uq_contenedor_ubicacion_activa",
            "ubicacion_id",
            unique=True,
            postgresql_where=(ubicacion_id.is_not(None)),
        ),
    )


class Movimiento(Base):
    __tablename__ = "movimientos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contenedor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contenedores.id"), nullable=False)
    patio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patios.id"), nullable=False)
    tipo: Mapped[TipoMovimiento] = mapped_column(Enum(TipoMovimiento, name="tipo_movimiento"), nullable=False)
    ubicacion_origen_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ubicaciones.id"), nullable=True
    )
    ubicacion_destino_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ubicaciones.id"), nullable=True
    )
    operador_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    ts: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    override_manual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    score_sugerido: Mapped[float | None] = mapped_column(nullable=True)
    score_elegido: Mapped[float | None] = mapped_column(nullable=True)
    motivo_override: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_movimiento_contenedor_ts", "contenedor_id", "ts"),)
```

- [ ] **Step 6: Registrar en `backend/app/models/__init__.py`**

```python
"""Importa todos los modelos para que Base.metadata los conozca (usado por Alembic)."""

from app.models.auditoria import Auditoria  # noqa: F401
from app.models.cliente import Cliente  # noqa: F401
from app.models.contenedor import Contenedor, Movimiento  # noqa: F401
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion  # noqa: F401
from app.models.usuario import Usuario, UsuarioPatio  # noqa: F401
```

- [ ] **Step 7: `backend/app/alembic/versions/0005_contenedor_movimiento.py`**

```python
"""contenedor movimiento

Revision ID: 0005_contenedor_movimiento
Revises: 0004_auditoria_rol_app
Create Date: 2026-09-14
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_contenedor_movimiento"
down_revision = "0004_auditoria_rol_app"
branch_labels = None
depends_on = None

tamano_contenedor = postgresql.ENUM("20", "40", "45", name="tamano_contenedor")
estado_contenedor = postgresql.ENUM(
    "solicitud_ingreso", "qr_ingreso_emitido", "en_porteria", "ingresado", "ubicado",
    "en_estadia", "en_servicio_especial", "solicitud_salida", "qr_salida_emitido",
    "en_porteria_salida", "despachado", "rechazado",
    name="estado_contenedor",
)
tipo_movimiento = postgresql.ENUM("ingreso", "reubicacion", "servicio", "salida", name="tipo_movimiento")


def upgrade() -> None:
    tamano_contenedor.create(op.get_bind())
    estado_contenedor.create(op.get_bind())
    tipo_movimiento.create(op.get_bind())

    op.create_table(
        "contenedores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("numero_contenedor", sa.String(11), nullable=False),
        sa.Column("tipo", postgresql.ENUM(name="tipo_contenedor", create_type=False), nullable=False),
        sa.Column("tamano", tamano_contenedor, nullable=False),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clientes.id"), nullable=True),
        sa.Column("patio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patios.id"), nullable=False),
        sa.Column("ubicacion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ubicaciones.id"), nullable=True),
        sa.Column("estado", estado_contenedor, nullable=False),
        sa.Column("peso_kg", sa.Integer(), nullable=False),
        sa.Column("fecha_estimada_salida", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "uq_contenedor_ubicacion_activa",
        "contenedores",
        ["ubicacion_id"],
        unique=True,
        postgresql_where=sa.text("ubicacion_id IS NOT NULL"),
    )

    op.create_table(
        "movimientos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("contenedor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contenedores.id"), nullable=False),
        sa.Column("patio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patios.id"), nullable=False),
        sa.Column("tipo", tipo_movimiento, nullable=False),
        sa.Column("ubicacion_origen_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ubicaciones.id"), nullable=True),
        sa.Column("ubicacion_destino_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ubicaciones.id"), nullable=True),
        sa.Column("operador_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("override_manual", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("score_sugerido", sa.Float(), nullable=True),
        sa.Column("score_elegido", sa.Float(), nullable=True),
        sa.Column("motivo_override", sa.Text(), nullable=True),
    )
    op.create_index("ix_movimiento_contenedor_ts", "movimientos", ["contenedor_id", "ts"])

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON contenedores, movimientos TO patio_app;")


def downgrade() -> None:
    op.drop_table("movimientos")
    op.drop_index("uq_contenedor_ubicacion_activa", table_name="contenedores")
    op.drop_table("contenedores")
    tipo_movimiento.drop(op.get_bind())
    estado_contenedor.drop(op.get_bind())
    tamano_contenedor.drop(op.get_bind())
```

- [ ] **Step 8: Correr tests, confirmar que pasan**

```bash
cd backend && pytest tests/test_contenedor_models.py -v
```
Esperado: PASS (5 tests)

- [ ] **Step 9: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/models backend/app/core/iso6346.py \
  backend/app/alembic/versions/0005_contenedor_movimiento.py \
  backend/tests/test_contenedor_models.py
git commit -m "feat: Contenedor/Movimiento, maquina de estados, checksum ISO 6346"
```

---

### Task 7: Seguridad — hashing de password + JWT

**Files:**
- Create: `backend/app/core/security.py`
- Test: `backend/tests/test_security.py`

**Interfaces:**
- Produces: `hash_password(password: str) -> str`, `verify_password(password: str, password_hash: str) -> bool`, `create_access_token(usuario_id: str, rol: str, patios: list[str], expires_minutes: int) -> str`, `decode_access_token(token: str) -> dict`
- Consumes: `app.config.settings` (Task 2)

- [ ] **Step 1: Escribir test que falla**

`backend/tests/test_security.py`:

```python
import jwt
import pytest

from app.config import settings
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_hash_password_no_es_texto_plano():
    hashed = hash_password("clave-secreta")
    assert hashed != "clave-secreta"
    assert verify_password("clave-secreta", hashed) is True
    assert verify_password("clave-incorrecta", hashed) is False


def test_create_access_token_contiene_claims_esperados():
    token = create_access_token("usr-1", "operador", ["patio-1"], expires_minutes=60)
    payload = decode_access_token(token)
    assert payload["sub"] == "usr-1"
    assert payload["rol"] == "operador"
    assert payload["patios"] == ["patio-1"]


def test_decode_access_token_rechaza_token_expirado():
    token = create_access_token("usr-1", "operador", [], expires_minutes=-1)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_decode_access_token_rechaza_firma_invalida():
    token = create_access_token("usr-1", "operador", [], expires_minutes=60)
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(tampered)
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd backend && pytest tests/test_security.py -v
```
Esperado: FAIL — `ModuleNotFoundError: No module named 'app.core.security'`

- [ ] **Step 3: `backend/app/core/security.py`**

```python
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


def create_access_token(usuario_id: str, rol: str, patios: list[str], expires_minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": usuario_id,
        "rol": rol,
        "patios": patios,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
```

- [ ] **Step 4: Correr tests, confirmar que pasan**

```bash
cd backend && pytest tests/test_security.py -v
```
Esperado: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/core/security.py backend/tests/test_security.py
git commit -m "feat: hashing bcrypt y JWT HS256 para auth"
```

---

### Task 8: RBAC (`get_current_user`, `require_roles`) + `POST /auth/login`

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/routes/__init__.py`
- Create: `backend/app/api/routes/auth.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/auth.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Produces: `CurrentUser` (dataclass: `id`, `rol: RolUsuario`, `patios: list[uuid.UUID]`), `get_current_user`, `require_roles(*roles)`, ruta `POST /api/auth/login`
- Consumes: `Usuario`, `UsuarioPatio` (Task 4), `create_access_token`/`verify_password` (Task 7)

- [ ] **Step 1: Escribir test que falla**

`backend/tests/test_auth.py`:

```python
import pytest

from app.core.security import hash_password
from app.models.enums import RolUsuario
from app.models.ubicacion import Patio
from app.models.usuario import Usuario, UsuarioPatio


@pytest.mark.anyio
async def test_login_correcto_devuelve_token(client, db_session):
    patio = Patio(nombre="Patio Norte", codigo="PN")
    db_session.add(patio)
    await db_session.flush()

    usuario = Usuario(
        tipo=RolUsuario.OPERADOR,
        email="operador@patio.mx",
        password_hash=hash_password("clave123"),
        activo=True,
    )
    db_session.add(usuario)
    await db_session.flush()
    db_session.add(UsuarioPatio(usuario_id=usuario.id, patio_id=patio.id))
    await db_session.commit()

    response = await client.post(
        "/api/auth/login", data={"username": "operador@patio.mx", "password": "clave123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert "access_token" in body


@pytest.mark.anyio
async def test_login_password_incorrecto_falla(client, db_session):
    usuario = Usuario(
        tipo=RolUsuario.OPERADOR,
        email="operador2@patio.mx",
        password_hash=hash_password("clave123"),
        activo=True,
    )
    db_session.add(usuario)
    await db_session.commit()

    response = await client.post(
        "/api/auth/login", data={"username": "operador2@patio.mx", "password": "incorrecta"}
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_endpoint_protegido_sin_token_devuelve_401(client):
    response = await client.get("/api/patios")
    assert response.status_code == 401
```

Nota: `test_endpoint_protegido_sin_token_devuelve_401` referencia `/api/patios`, que se implementa en Task 9 — este caso se agrega a `test_auth.py` en Task 9, no aquí. Quitar esa función de este archivo por ahora.

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd backend && pytest tests/test_auth.py -v
```
Esperado: FAIL — `404 Not Found` en `/api/auth/login` (ruta no existe todavía)

- [ ] **Step 3: `backend/app/schemas/__init__.py`** (vacío) y **`backend/app/schemas/auth.py`**

```python
from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

- [ ] **Step 4: `backend/app/api/__init__.py`**, **`backend/app/api/routes/__init__.py`** (vacíos)

- [ ] **Step 5: `backend/app/api/routes/auth.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import create_access_token, verify_password
from app.db import get_db
from app.models.usuario import Usuario, UsuarioPatio
from app.schemas.auth import TokenResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    result = await db.execute(
        select(Usuario).where(Usuario.email == form.username, Usuario.activo.is_(True))
    )
    usuario = result.scalar_one_or_none()
    if (
        usuario is None
        or usuario.password_hash is None
        or not verify_password(form.password, usuario.password_hash)
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")

    patios_result = await db.execute(
        select(UsuarioPatio.patio_id).where(UsuarioPatio.usuario_id == usuario.id)
    )
    patios = [str(row[0]) for row in patios_result.all()]

    token = create_access_token(str(usuario.id), usuario.tipo.value, patios, settings.jwt_expires_minutes)
    return TokenResponse(access_token=token)
```

- [ ] **Step 6: `backend/app/api/deps.py`**

```python
import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db import get_db
from app.models.enums import RolUsuario
from app.models.usuario import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@dataclass
class CurrentUser:
    id: uuid.UUID
    rol: RolUsuario
    patios: list[uuid.UUID]


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> CurrentUser:
    try:
        payload = decode_access_token(token)
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")

    usuario_id = uuid.UUID(payload["sub"])
    result = await db.execute(
        select(Usuario).where(Usuario.id == usuario_id, Usuario.activo.is_(True))
    )
    usuario = result.scalar_one_or_none()
    if usuario is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no encontrado")

    return CurrentUser(
        id=usuario.id,
        rol=RolUsuario(payload["rol"]),
        patios=[uuid.UUID(p) for p in payload.get("patios", [])],
    )


def require_roles(*roles: RolUsuario):
    async def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.rol not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No autorizado para este recurso")
        return user

    return dependency
```

- [ ] **Step 7: Montar router en `backend/app/main.py`**

```python
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import auth
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
```

- [ ] **Step 8: Correr tests, confirmar que pasan**

```bash
cd backend && pytest tests/test_auth.py -v
```
Esperado: PASS (2 tests — `test_endpoint_protegido_sin_token_devuelve_401` se agrega en Task 9)

- [ ] **Step 9: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/schemas backend/app/api backend/app/main.py backend/tests/test_auth.py
git commit -m "feat: RBAC (get_current_user, require_roles) y POST /auth/login"
```

---

### Task 9: CRUD Patios/Ubicaciones (admin) con auditoría

**Files:**
- Create: `backend/app/schemas/patio.py`
- Create: `backend/app/api/routes/patios.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_auth.py` (agrega el caso 401 pendiente de Task 8)
- Test: `backend/tests/test_patios_api.py`

**Interfaces:**
- Produces: `POST /api/patios` (admin), `GET /api/patios` (cualquier rol interno), `POST /api/patios/{id}/carriles` (admin)
- Consumes: `require_roles`, `get_current_user` (Task 8), `registrar_auditoria` (Task 5)

- [ ] **Step 1: Escribir test que falla**

`backend/tests/test_patios_api.py`:

```python
import pytest

from app.core.security import create_access_token
from app.models.enums import RolUsuario


def _token(rol: RolUsuario, patios: list[str] | None = None) -> str:
    return create_access_token("00000000-0000-0000-0000-000000000001", rol.value, patios or [], 60)


@pytest.mark.anyio
async def test_admin_crea_patio(client):
    token = _token(RolUsuario.ADMIN)
    response = await client.post(
        "/api/patios",
        json={"nombre": "Patio Norte", "codigo": "PN"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["codigo"] == "PN"


@pytest.mark.anyio
async def test_operador_no_puede_crear_patio(client):
    token = _token(RolUsuario.OPERADOR)
    response = await client.post(
        "/api/patios",
        json={"nombre": "Patio Norte", "codigo": "PN2"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.anyio
async def test_listar_patios(client):
    token = _token(RolUsuario.ADMIN)
    await client.post(
        "/api/patios", json={"nombre": "Patio Sur", "codigo": "PS"},
        headers={"Authorization": f"Bearer {token}"},
    )
    response = await client.get("/api/patios", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert any(p["codigo"] == "PS" for p in response.json())
```

Nota: en `backend/tests/test_auth.py`, agregar el caso pendiente de Task 8:

```python
@pytest.mark.anyio
async def test_endpoint_protegido_sin_token_devuelve_401(client):
    response = await client.get("/api/patios")
    assert response.status_code == 401
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd backend && pytest tests/test_patios_api.py tests/test_auth.py -v
```
Esperado: FAIL — `404 Not Found` en `/api/patios`

- [ ] **Step 3: `backend/app/schemas/patio.py`**

```python
import uuid

from pydantic import BaseModel, ConfigDict


class PatioCreate(BaseModel):
    nombre: str
    codigo: str


class PatioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    codigo: str
    activo: bool
```

- [ ] **Step 4: `backend/app/api/routes/patios.py`**

```python
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.core.auditoria import registrar_auditoria
from app.db import get_db
from app.models.enums import RolUsuario
from app.models.ubicacion import Patio
from app.schemas.patio import PatioCreate, PatioOut

router = APIRouter()


@router.post("", response_model=PatioOut, status_code=status.HTTP_201_CREATED)
async def crear_patio(
    payload: PatioCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.ADMIN)),
) -> Patio:
    patio = Patio(nombre=payload.nombre, codigo=payload.codigo)
    db.add(patio)
    await db.flush()

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="crear",
        entidad="patios",
        entidad_id=str(patio.id),
        valor_anterior=None,
        valor_nuevo={"nombre": patio.nombre, "codigo": patio.codigo},
        patio_id=patio.id,
    )
    await db.commit()
    return patio


@router.get("", response_model=list[PatioOut])
async def listar_patios(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> list[Patio]:
    result = await db.execute(select(Patio))
    return list(result.scalars().all())
```

- [ ] **Step 5: Montar router en `backend/app/main.py`**

```python
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import auth, patios
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
```

- [ ] **Step 6: Correr tests, confirmar que pasan**

```bash
cd backend && pytest tests/test_patios_api.py tests/test_auth.py -v
```
Esperado: PASS (4 tests)

- [ ] **Step 7: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/schemas/patio.py backend/app/api/routes/patios.py backend/app/main.py \
  backend/tests/test_patios_api.py backend/tests/test_auth.py
git commit -m "feat: CRUD patios (admin) con auditoria"
```

---

### Task 10: CRUD Contenedores con checksum ISO 6346 + auditoría

**Files:**
- Create: `backend/app/schemas/contenedor.py`
- Create: `backend/app/api/routes/contenedores.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_contenedores_api.py`

**Interfaces:**
- Produces: `POST /api/contenedores` (operador/supervisor/admin), `GET /api/contenedores/{id}`
- Consumes: `validar_iso6346` (Task 6), `require_roles` (Task 8), `registrar_auditoria` (Task 5)

- [ ] **Step 1: Escribir test que falla**

`backend/tests/test_contenedores_api.py`:

```python
import pytest

from app.core.security import create_access_token
from app.models.enums import RolUsuario


def _token(rol: RolUsuario) -> str:
    return create_access_token("00000000-0000-0000-0000-000000000001", rol.value, [], 60)


@pytest.mark.anyio
async def test_operador_crea_contenedor(client):
    admin_token = _token(RolUsuario.ADMIN)
    patio_resp = await client.post(
        "/api/patios", json={"nombre": "Patio Norte", "codigo": "PN"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    patio_id = patio_resp.json()["id"]

    op_token = _token(RolUsuario.OPERADOR)
    response = await client.post(
        "/api/contenedores",
        json={
            "numero_contenedor": "CSQU3054383",
            "tipo": "lleno",
            "tamano": "40",
            "patio_id": patio_id,
            "peso_kg": 18000,
        },
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["numero_contenedor"] == "CSQU3054383"
    assert body["estado"] == "solicitud_ingreso"


@pytest.mark.anyio
async def test_numero_contenedor_invalido_rechazado(client):
    admin_token = _token(RolUsuario.ADMIN)
    patio_resp = await client.post(
        "/api/patios", json={"nombre": "Patio Norte", "codigo": "PN2"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    patio_id = patio_resp.json()["id"]

    op_token = _token(RolUsuario.OPERADOR)
    response = await client.post(
        "/api/contenedores",
        json={
            "numero_contenedor": "CSQU3054380",
            "tipo": "lleno",
            "tamano": "40",
            "patio_id": patio_id,
            "peso_kg": 18000,
        },
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_cliente_no_puede_crear_contenedor(client):
    admin_token = _token(RolUsuario.ADMIN)
    patio_resp = await client.post(
        "/api/patios", json={"nombre": "Patio Norte", "codigo": "PN3"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    patio_id = patio_resp.json()["id"]

    cliente_token = _token(RolUsuario.CLIENTE)
    response = await client.post(
        "/api/contenedores",
        json={
            "numero_contenedor": "CSQU3054383",
            "tipo": "lleno",
            "tamano": "40",
            "patio_id": patio_id,
            "peso_kg": 18000,
        },
        headers={"Authorization": f"Bearer {cliente_token}"},
    )
    assert response.status_code == 403
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd backend && pytest tests/test_contenedores_api.py -v
```
Esperado: FAIL — `404 Not Found` en `/api/contenedores`

- [ ] **Step 3: `backend/app/schemas/contenedor.py`**

```python
import uuid

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.iso6346 import validar_iso6346
from app.models.enums import EstadoContenedor, TamanoContenedor, TipoContenedor


class ContenedorCreate(BaseModel):
    numero_contenedor: str
    tipo: TipoContenedor
    tamano: TamanoContenedor
    patio_id: uuid.UUID
    peso_kg: int

    @field_validator("numero_contenedor")
    @classmethod
    def numero_valido(cls, value: str) -> str:
        value = value.strip().upper()
        if not validar_iso6346(value):
            raise ValueError("numero_contenedor no cumple el checksum ISO 6346")
        return value


class ContenedorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    numero_contenedor: str
    tipo: TipoContenedor
    tamano: TamanoContenedor
    patio_id: uuid.UUID
    estado: EstadoContenedor
    peso_kg: int
```

- [ ] **Step 4: `backend/app/api/routes/contenedores.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.core.auditoria import registrar_auditoria
from app.db import get_db
from app.models.contenedor import Contenedor
from app.models.enums import EstadoContenedor, RolUsuario
from app.schemas.contenedor import ContenedorCreate, ContenedorOut

router = APIRouter()

_ROLES_ESCRITURA = (RolUsuario.OPERADOR, RolUsuario.SUPERVISOR, RolUsuario.ADMIN)


@router.post("", response_model=ContenedorOut, status_code=status.HTTP_201_CREATED)
async def crear_contenedor(
    payload: ContenedorCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Contenedor:
    contenedor = Contenedor(
        numero_contenedor=payload.numero_contenedor,
        tipo=payload.tipo,
        tamano=payload.tamano,
        patio_id=payload.patio_id,
        estado=EstadoContenedor.SOLICITUD_INGRESO,
        peso_kg=payload.peso_kg,
    )
    db.add(contenedor)
    await db.flush()

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="crear",
        entidad="contenedores",
        entidad_id=str(contenedor.id),
        valor_anterior=None,
        valor_nuevo={"numero_contenedor": contenedor.numero_contenedor, "estado": contenedor.estado.value},
        patio_id=contenedor.patio_id,
    )
    await db.commit()
    return contenedor


@router.get("/{contenedor_id}", response_model=ContenedorOut)
async def obtener_contenedor(
    contenedor_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> Contenedor:
    result = await db.execute(select(Contenedor).where(Contenedor.id == contenedor_id))
    contenedor = result.scalar_one_or_none()
    if contenedor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado")
    return contenedor
```

- [ ] **Step 5: Montar router en `backend/app/main.py`**

```python
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import auth, contenedores, patios
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
```

- [ ] **Step 6: Correr tests, confirmar que pasan**

```bash
cd backend && pytest tests/test_contenedores_api.py -v
```
Esperado: PASS (3 tests)

- [ ] **Step 7: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/schemas/contenedor.py backend/app/api/routes/contenedores.py \
  backend/app/main.py backend/tests/test_contenedores_api.py
git commit -m "feat: CRUD contenedores con validacion ISO 6346 y auditoria"
```

---

### Task 11: `POST /movimientos` — locking y transición de estado

**Files:**
- Create: `backend/app/schemas/ubicacion.py` (parte 1: esquema de movimiento)
- Create: `backend/app/api/routes/movimientos.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_movimientos_api.py`

**Interfaces:**
- Produces: `POST /api/movimientos` (operador/supervisor/admin) — bloquea el slot destino con `SELECT ... FOR UPDATE SKIP LOCKED`, rechaza si está ocupado, actualiza `contenedor.ubicacion_id`/`estado`, inserta `Movimiento` + auditoría
- Consumes: `Contenedor`, `Movimiento`, `Ubicacion` (Tasks 3, 6), `registrar_auditoria` (Task 5)

- [ ] **Step 1: Escribir test que falla**

`backend/tests/test_movimientos_api.py`:

```python
import pytest

from app.core.security import create_access_token
from app.models.enums import RolUsuario


def _token(rol: RolUsuario) -> str:
    return create_access_token("00000000-0000-0000-0000-000000000001", rol.value, [], 60)


async def _crear_patio_carril_tramo_tira_ubicacion(client, admin_token, sufijo):
    patio = (
        await client.post(
            "/api/patios", json={"nombre": f"Patio {sufijo}", "codigo": f"P{sufijo}"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    ).json()
    return patio


@pytest.mark.anyio
async def test_registrar_movimiento_ubica_contenedor(client, db_session):
    from app.models.ubicacion import Carril, Tira, Tramo, Ubicacion

    admin_token = _token(RolUsuario.ADMIN)
    patio = await _crear_patio_carril_tramo_tira_ubicacion(client, admin_token, "M1")

    carril = Carril(patio_id=patio["id"], codigo="A1", orden=0)
    db_session.add(carril)
    await db_session.flush()
    tramo = Tramo(carril_id=carril.id, codigo="T1", orden=0)
    db_session.add(tramo)
    await db_session.flush()
    tira = Tira(tramo_id=tramo.id, codigo="S1", orden=0)
    db_session.add(tira)
    await db_session.flush()
    ubicacion = Ubicacion(tira_id=tira.id, nivel=1, codigo="A1-T1-S1-N1")
    db_session.add(ubicacion)
    await db_session.commit()

    op_token = _token(RolUsuario.OPERADOR)
    contenedor_resp = await client.post(
        "/api/contenedores",
        json={
            "numero_contenedor": "CSQU3054383",
            "tipo": "lleno",
            "tamano": "40",
            "patio_id": patio["id"],
            "peso_kg": 18000,
        },
        headers={"Authorization": f"Bearer {op_token}"},
    )
    contenedor_id = contenedor_resp.json()["id"]

    response = await client.post(
        "/api/movimientos",
        json={
            "contenedor_id": contenedor_id,
            "ubicacion_destino_id": str(ubicacion.id),
            "tipo": "ingreso",
        },
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert response.status_code == 201

    verificar = await client.get(
        f"/api/contenedores/{contenedor_id}", headers={"Authorization": f"Bearer {op_token}"}
    )
    assert verificar.json()["estado"] == "ubicado"


@pytest.mark.anyio
async def test_no_permite_mover_a_slot_ocupado(client, db_session):
    from app.models.ubicacion import Carril, Tira, Tramo, Ubicacion

    admin_token = _token(RolUsuario.ADMIN)
    patio = await _crear_patio_carril_tramo_tira_ubicacion(client, admin_token, "M2")

    carril = Carril(patio_id=patio["id"], codigo="A1", orden=0)
    db_session.add(carril)
    await db_session.flush()
    tramo = Tramo(carril_id=carril.id, codigo="T1", orden=0)
    db_session.add(tramo)
    await db_session.flush()
    tira = Tira(tramo_id=tramo.id, codigo="S1", orden=0)
    db_session.add(tira)
    await db_session.flush()
    ubicacion = Ubicacion(tira_id=tira.id, nivel=1, codigo="A1-T1-S1-N1")
    db_session.add(ubicacion)
    await db_session.commit()

    op_token = _token(RolUsuario.OPERADOR)

    async def _crear_y_mover(numero: str) -> int:
        contenedor_resp = await client.post(
            "/api/contenedores",
            json={
                "numero_contenedor": numero,
                "tipo": "lleno",
                "tamano": "40",
                "patio_id": patio["id"],
                "peso_kg": 18000,
            },
            headers={"Authorization": f"Bearer {op_token}"},
        )
        contenedor_id = contenedor_resp.json()["id"]
        mov = await client.post(
            "/api/movimientos",
            json={"contenedor_id": contenedor_id, "ubicacion_destino_id": str(ubicacion.id), "tipo": "ingreso"},
            headers={"Authorization": f"Bearer {op_token}"},
        )
        return mov.status_code

    primer_status = await _crear_y_mover("CSQU3054383")
    segundo_status = await _crear_y_mover("TRHU1866154")

    assert primer_status == 201
    assert segundo_status == 409
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd backend && pytest tests/test_movimientos_api.py -v
```
Esperado: FAIL — `404 Not Found` en `/api/movimientos`

- [ ] **Step 3: `backend/app/schemas/ubicacion.py`**

```python
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
```

- [ ] **Step 4: `backend/app/api/routes/movimientos.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.core.auditoria import registrar_auditoria
from app.db import get_db
from app.models.contenedor import Contenedor, Movimiento
from app.models.enums import EstadoContenedor, RolUsuario
from app.models.ubicacion import Ubicacion
from app.schemas.ubicacion import MovimientoCreate, MovimientoOut

router = APIRouter()

_ROLES_ESCRITURA = (RolUsuario.OPERADOR, RolUsuario.SUPERVISOR, RolUsuario.ADMIN)


@router.post("", response_model=MovimientoOut, status_code=status.HTTP_201_CREATED)
async def registrar_movimiento(
    payload: MovimientoCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Movimiento:
    ubicacion_result = await db.execute(
        select(Ubicacion).where(Ubicacion.id == payload.ubicacion_destino_id).with_for_update()
    )
    ubicacion = ubicacion_result.scalar_one_or_none()
    if ubicacion is None or not ubicacion.activo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ubicación no encontrada")

    ocupado_result = await db.execute(
        select(Contenedor.id).where(Contenedor.ubicacion_id == payload.ubicacion_destino_id)
    )
    if ocupado_result.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ubicación ya ocupada")

    contenedor_result = await db.execute(select(Contenedor).where(Contenedor.id == payload.contenedor_id))
    contenedor = contenedor_result.scalar_one_or_none()
    if contenedor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado")

    origen_id = contenedor.ubicacion_id
    contenedor.ubicacion_id = payload.ubicacion_destino_id
    contenedor.estado = EstadoContenedor.UBICADO

    movimiento = Movimiento(
        contenedor_id=contenedor.id,
        patio_id=contenedor.patio_id,
        tipo=payload.tipo,
        ubicacion_origen_id=origen_id,
        ubicacion_destino_id=payload.ubicacion_destino_id,
        operador_id=user.id,
        override_manual=payload.override_manual,
        motivo_override=payload.motivo_override,
        score_sugerido=payload.score_sugerido,
        score_elegido=payload.score_elegido,
    )
    db.add(movimiento)
    await db.flush()

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="mover",
        entidad="contenedores",
        entidad_id=str(contenedor.id),
        valor_anterior={"ubicacion_id": str(origen_id) if origen_id else None},
        valor_nuevo={"ubicacion_id": str(payload.ubicacion_destino_id)},
        patio_id=contenedor.patio_id,
    )
    await db.commit()
    return movimiento
```

- [ ] **Step 5: Montar router en `backend/app/main.py`**

```python
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import auth, contenedores, movimientos, patios
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
```

- [ ] **Step 6: Correr tests, confirmar que pasan**

```bash
cd backend && pytest tests/test_movimientos_api.py -v
```
Esperado: PASS (2 tests)

- [ ] **Step 7: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/schemas/ubicacion.py backend/app/api/routes/movimientos.py \
  backend/app/main.py backend/tests/test_movimientos_api.py
git commit -m "feat: POST /movimientos con locking de slot y transicion de estado"
```

---

### Task 12: Algoritmo de sugerencia de ubicación

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/ubicacion_algoritmo.py`
- Modify: `backend/app/schemas/ubicacion.py`
- Modify: `backend/app/api/routes/movimientos.py` → nuevo archivo `backend/app/api/routes/ubicaciones.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_ubicacion_algoritmo.py`

**Interfaces:**
- Produces: `Coordenadas`, `distancia_manhattan(a, b) -> int`, `calcular_costo(db, ubicacion, contenedor, punto_referencia) -> float`, `sugerir_ubicacion(db, patio_id, contenedor, punto_referencia_ubicacion_id) -> CandidatoUbicacion`, ruta `POST /api/ubicaciones/sugerir`
- Consumes: `Ubicacion`, `Carril`, `Tramo`, `Tira`, `Contenedor` (Tasks 3, 6)

**Fórmula implementada** (pesos y penalizaciones — ver spec artifact sección 8 para la justificación funcional; las constantes exactas de penalización quedan fijadas aquí como la versión autoritativa, ya que el documento de spec usa valores ilustrativos redondeados):

```
costo = 0.40·D_manhattan + 0.25·pen_tipo + 0.15·pen_peso + 0.15·pen_bloqueo + 0.05·pen_destino

pen_tipo    = 0.0 si carril.tipo_teorico is None o == contenedor.tipo, si no 0.3
pen_peso    = 0.0 si nivel==1; si no, 0.0 si peso_contenedor <= peso_contenedor_abajo, si no 1.0
pen_bloqueo = (5 - nivel) / 4 * 0.6
pen_destino = 0.0 si no hay fecha_estimada_salida; si no, distancia_normalizada * (0.8 si <=48h restantes, si no 0.2)
```

- [ ] **Step 1: Escribir test que falla**

`backend/tests/test_ubicacion_algoritmo.py`:

```python
import pytest

from app.models.cliente import Cliente
from app.models.contenedor import Contenedor
from app.models.enums import EstadoContenedor, TamanoContenedor, TipoCliente, TipoContenedor
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion
from app.services.ubicacion_algoritmo import sugerir_ubicacion


async def _crear_estructura(db_session, *, carril_a_orden, carril_a_tipo, carril_b_orden, carril_b_tipo):
    patio = Patio(nombre="Patio Test", codigo=f"PT-{carril_a_orden}-{carril_b_orden}")
    db_session.add(patio)
    await db_session.flush()

    carril_a = Carril(patio_id=patio.id, codigo="A1", orden=carril_a_orden, tipo_teorico=carril_a_tipo)
    carril_b = Carril(patio_id=patio.id, codigo="A2", orden=carril_b_orden, tipo_teorico=carril_b_tipo)
    db_session.add_all([carril_a, carril_b])
    await db_session.flush()

    tramo_a = Tramo(carril_id=carril_a.id, codigo="T1", orden=0)
    tramo_b = Tramo(carril_id=carril_b.id, codigo="T1", orden=0)
    db_session.add_all([tramo_a, tramo_b])
    await db_session.flush()

    tira_a = Tira(tramo_id=tramo_a.id, codigo="S1", orden=0)
    tira_b = Tira(tramo_id=tramo_b.id, codigo="S1", orden=0)
    db_session.add_all([tira_a, tira_b])
    await db_session.flush()

    ubicacion_a = Ubicacion(tira_id=tira_a.id, nivel=1, codigo="A1-T1-S1-N1")
    ubicacion_b = Ubicacion(tira_id=tira_b.id, nivel=1, codigo="A2-T1-S1-N1")
    db_session.add_all([ubicacion_a, ubicacion_b])
    await db_session.flush()

    return patio, ubicacion_a, ubicacion_b


@pytest.mark.anyio
async def test_prefiere_slot_mas_cercano_aunque_sea_zona_teorica_distinta(db_session):
    patio, ubicacion_a1_lleno, ubicacion_a2_vacio = await _crear_estructura(
        db_session,
        carril_a_orden=0,
        carril_a_tipo=TipoContenedor.LLENO,
        carril_b_orden=3,
        carril_b_tipo=TipoContenedor.VACIO,
    )

    cliente = Cliente(razon_social="Importadora X", rfc="IMX010101AA1", tipo=TipoCliente.IMPORTADOR_EXPORTADOR)
    db_session.add(cliente)
    await db_session.flush()

    contenedor_lleno = Contenedor(
        numero_contenedor="CSQU3054383",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.CUARENTA,
        cliente_id=cliente.id,
        patio_id=patio.id,
        estado=EstadoContenedor.INGRESADO,
        peso_kg=18000,
    )
    db_session.add(contenedor_lleno)
    await db_session.flush()

    resultado = await sugerir_ubicacion(
        db_session,
        patio_id=patio.id,
        contenedor=contenedor_lleno,
        punto_referencia_ubicacion_id=ubicacion_a2_vacio.id,
    )

    assert resultado.ubicacion_id == ubicacion_a2_vacio.id


@pytest.mark.anyio
async def test_no_sugiere_nivel_sin_base(db_session):
    patio, ubicacion_a1, _ = await _crear_estructura(
        db_session, carril_a_orden=0, carril_a_tipo=None, carril_b_orden=1, carril_b_tipo=None
    )
    nivel2 = Ubicacion(tira_id=ubicacion_a1.tira_id, nivel=2, codigo="A1-T1-S1-N2")
    db_session.add(nivel2)
    await db_session.flush()

    cliente = Cliente(razon_social="Importadora X", rfc="IMX020202AA1", tipo=TipoCliente.IMPORTADOR_EXPORTADOR)
    db_session.add(cliente)
    await db_session.flush()

    contenedor = Contenedor(
        numero_contenedor="CSQU3054383",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.CUARENTA,
        cliente_id=cliente.id,
        patio_id=patio.id,
        estado=EstadoContenedor.INGRESADO,
        peso_kg=18000,
    )
    db_session.add(contenedor)
    await db_session.flush()

    resultado = await sugerir_ubicacion(
        db_session, patio_id=patio.id, contenedor=contenedor, punto_referencia_ubicacion_id=ubicacion_a1.id
    )
    assert resultado.ubicacion_id == ubicacion_a1.id
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd backend && pytest tests/test_ubicacion_algoritmo.py -v
```
Esperado: FAIL — `ModuleNotFoundError: No module named 'app.services.ubicacion_algoritmo'`

- [ ] **Step 3: `backend/app/services/__init__.py`** (vacío) y **`backend/app/services/ubicacion_algoritmo.py`**

```python
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contenedor import Contenedor
from app.models.ubicacion import Carril, Tira, Tramo, Ubicacion

PESO_DISTANCIA = 0.40
PESO_TIPO = 0.25
PESO_PESO = 0.15
PESO_BLOQUEO = 0.15
PESO_DESTINO = 0.05
MAX_DISTANCIA_PATIO = 20


@dataclass(frozen=True)
class Coordenadas:
    carril_orden: int
    tramo_orden: int
    tira_orden: int
    nivel: int


@dataclass(frozen=True)
class CandidatoUbicacion:
    ubicacion_id: uuid.UUID
    codigo: str
    costo: float


def distancia_manhattan(a: Coordenadas, b: Coordenadas) -> int:
    return (
        abs(a.carril_orden - b.carril_orden)
        + abs(a.tramo_orden - b.tramo_orden)
        + abs(a.tira_orden - b.tira_orden)
        + abs(a.nivel - b.nivel)
    )


async def _coordenadas_de_ubicacion(db: AsyncSession, ubicacion: Ubicacion) -> Coordenadas:
    result = await db.execute(
        select(Tira.orden, Tramo.orden, Carril.orden)
        .join(Tramo, Tira.tramo_id == Tramo.id)
        .join(Carril, Tramo.carril_id == Carril.id)
        .where(Tira.id == ubicacion.tira_id)
    )
    tira_orden, tramo_orden, carril_orden = result.one()
    return Coordenadas(carril_orden, tramo_orden, tira_orden, ubicacion.nivel)


async def _contenedor_en_nivel_inferior(
    db: AsyncSession, tira_id: uuid.UUID, nivel: int
) -> Contenedor | None:
    if nivel <= 1:
        return None
    result = await db.execute(
        select(Contenedor)
        .join(Ubicacion, Contenedor.ubicacion_id == Ubicacion.id)
        .where(Ubicacion.tira_id == tira_id, Ubicacion.nivel == nivel - 1)
    )
    return result.scalar_one_or_none()


async def _tipo_teorico_carril(db: AsyncSession, tira_id: uuid.UUID):
    result = await db.execute(
        select(Carril.tipo_teorico)
        .join(Tramo, Tramo.carril_id == Carril.id)
        .join(Tira, Tira.tramo_id == Tramo.id)
        .where(Tira.id == tira_id)
    )
    return result.scalar_one_or_none()


async def calcular_costo(
    db: AsyncSession, ubicacion: Ubicacion, contenedor: Contenedor, punto_referencia: Coordenadas
) -> float:
    coords = await _coordenadas_de_ubicacion(db, ubicacion)
    d = distancia_manhattan(coords, punto_referencia)

    tipo_teorico = await _tipo_teorico_carril(db, ubicacion.tira_id)
    pen_tipo = 0.0 if tipo_teorico is None or tipo_teorico == contenedor.tipo else 0.3

    if ubicacion.nivel == 1:
        pen_peso = 0.0
    else:
        contenedor_abajo = await _contenedor_en_nivel_inferior(db, ubicacion.tira_id, ubicacion.nivel)
        if contenedor_abajo is None or contenedor.peso_kg > contenedor_abajo.peso_kg:
            pen_peso = 1.0
        else:
            pen_peso = 0.0

    pen_bloqueo = round((5 - ubicacion.nivel) / 4 * 0.6, 4)

    if contenedor.fecha_estimada_salida is None:
        pen_destino = 0.0
    else:
        horas_restantes = (
            contenedor.fecha_estimada_salida - datetime.now(timezone.utc)
        ).total_seconds() / 3600
        normalizado = min(d / MAX_DISTANCIA_PATIO, 1.0)
        factor = 0.8 if horas_restantes <= 48 else 0.2
        pen_destino = normalizado * factor

    return (
        PESO_DISTANCIA * d
        + PESO_TIPO * pen_tipo
        + PESO_PESO * pen_peso
        + PESO_BLOQUEO * pen_bloqueo
        + PESO_DESTINO * pen_destino
    )


async def sugerir_ubicacion(
    db: AsyncSession,
    *,
    patio_id: uuid.UUID,
    contenedor: Contenedor,
    punto_referencia_ubicacion_id: uuid.UUID,
) -> CandidatoUbicacion:
    ref_result = await db.execute(select(Ubicacion).where(Ubicacion.id == punto_referencia_ubicacion_id))
    ref_ubicacion = ref_result.scalar_one()
    punto_referencia = await _coordenadas_de_ubicacion(db, ref_ubicacion)

    libres_result = await db.execute(
        select(Ubicacion)
        .join(Tira, Ubicacion.tira_id == Tira.id)
        .join(Tramo, Tira.tramo_id == Tramo.id)
        .join(Carril, Tramo.carril_id == Carril.id)
        .outerjoin(Contenedor, Contenedor.ubicacion_id == Ubicacion.id)
        .where(Carril.patio_id == patio_id, Ubicacion.activo.is_(True), Contenedor.id.is_(None))
    )
    candidatos_libres = libres_result.scalars().all()

    evaluados: list[CandidatoUbicacion] = []
    for ubicacion in candidatos_libres:
        if ubicacion.nivel > 1:
            abajo = await _contenedor_en_nivel_inferior(db, ubicacion.tira_id, ubicacion.nivel)
            if abajo is None:
                continue
        costo = await calcular_costo(db, ubicacion, contenedor, punto_referencia)
        evaluados.append(CandidatoUbicacion(ubicacion.id, ubicacion.codigo, costo))

    if not evaluados:
        raise ValueError("No hay ubicaciones disponibles que cumplan las restricciones")

    evaluados.sort(key=lambda c: c.costo)
    return evaluados[0]
```

- [ ] **Step 4: Correr tests, confirmar que pasan**

```bash
cd backend && pytest tests/test_ubicacion_algoritmo.py -v
```
Esperado: PASS (2 tests)

- [ ] **Step 5: Exponer endpoint `POST /api/ubicaciones/sugerir`**

Agregar a `backend/app/schemas/ubicacion.py`:

```python
class SugerenciaUbicacionRequest(BaseModel):
    patio_id: uuid.UUID
    contenedor_id: uuid.UUID
    punto_referencia_ubicacion_id: uuid.UUID


class SugerenciaUbicacionResponse(BaseModel):
    ubicacion_id: uuid.UUID
    codigo: str
    costo: float
```

`backend/app/api/routes/ubicaciones.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.db import get_db
from app.models.contenedor import Contenedor
from app.models.enums import RolUsuario
from app.schemas.ubicacion import SugerenciaUbicacionRequest, SugerenciaUbicacionResponse
from app.services.ubicacion_algoritmo import sugerir_ubicacion

router = APIRouter()

_ROLES = (RolUsuario.OPERADOR, RolUsuario.SUPERVISOR, RolUsuario.ADMIN)


@router.post("/sugerir", response_model=SugerenciaUbicacionResponse)
async def sugerir(
    payload: SugerenciaUbicacionRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES)),
) -> SugerenciaUbicacionResponse:
    contenedor_result = await db.execute(select(Contenedor).where(Contenedor.id == payload.contenedor_id))
    contenedor = contenedor_result.scalar_one_or_none()
    if contenedor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado")

    try:
        candidato = await sugerir_ubicacion(
            db,
            patio_id=payload.patio_id,
            contenedor=contenedor,
            punto_referencia_ubicacion_id=payload.punto_referencia_ubicacion_id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))

    return SugerenciaUbicacionResponse(
        ubicacion_id=candidato.ubicacion_id, codigo=candidato.codigo, costo=candidato.costo
    )
```

Montar en `backend/app/main.py` (agregar `from app.api.routes import ubicaciones` y `app.include_router(ubicaciones.router, prefix="/api/ubicaciones", tags=["ubicaciones"])`).

- [ ] **Step 6: Correr toda la suite, confirmar que pasa**

```bash
cd backend && pytest -v
```
Esperado: PASS (todos los tests hasta este punto)

- [ ] **Step 7: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/services backend/app/schemas/ubicacion.py \
  backend/app/api/routes/ubicaciones.py backend/app/main.py \
  backend/tests/test_ubicacion_algoritmo.py
git commit -m "feat: algoritmo de sugerencia de ubicacion por scoring"
```

---

### Task 13: RLS por `patio_id`

**Files:**
- Create: `backend/app/alembic/versions/0006_rls_policies.py`
- Modify: `backend/app/api/deps.py`
- Modify: `backend/app/api/routes/contenedores.py` (usa `get_scoped_db` en `obtener_contenedor`)
- Test: `backend/tests/test_rls.py`

**Interfaces:**
- Produces: `get_scoped_db(user: CurrentUser, db: AsyncSession) -> AsyncSession` — inyecta `SET LOCAL app.rol` / `SET LOCAL app.patios_asignados` antes de devolver la sesión
- Consumes: `CurrentUser`, `get_current_user` (Task 8), tablas `contenedores`, `movimientos`, `auditoria` (Tasks 5–6)

- [ ] **Step 1: Escribir test que falla**

`backend/tests/test_rls.py`:

```python
import os

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.contenedor import Contenedor
from app.models.enums import EstadoContenedor, RolUsuario, TamanoContenedor, TipoContenedor
from app.models.ubicacion import Patio


@pytest.mark.anyio
async def test_operador_solo_ve_contenedores_de_su_patio(db_session):
    patio_1 = Patio(nombre="Patio Uno", codigo="RLS1")
    patio_2 = Patio(nombre="Patio Dos", codigo="RLS2")
    db_session.add_all([patio_1, patio_2])
    await db_session.flush()

    db_session.add_all(
        [
            Contenedor(
                numero_contenedor="CSQU3054383", tipo=TipoContenedor.LLENO, tamano=TamanoContenedor.CUARENTA,
                patio_id=patio_1.id, estado=EstadoContenedor.SOLICITUD_INGRESO, peso_kg=18000,
            ),
            Contenedor(
                numero_contenedor="TRHU1866154", tipo=TipoContenedor.LLENO, tamano=TamanoContenedor.CUARENTA,
                patio_id=patio_2.id, estado=EstadoContenedor.SOLICITUD_INGRESO, peso_kg=15000,
            ),
        ]
    )
    await db_session.commit()

    app_engine = create_async_engine(os.environ["DATABASE_URL"])
    session_factory = async_sessionmaker(app_engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as scoped_session:
        await scoped_session.execute(text("SET app.rol = :rol"), {"rol": RolUsuario.OPERADOR.value})
        await scoped_session.execute(
            text("SET app.patios_asignados = :patios"), {"patios": str(patio_1.id)}
        )
        result = await scoped_session.execute(select(Contenedor))
        visibles = result.scalars().all()

    await app_engine.dispose()

    assert len(visibles) == 1
    assert visibles[0].patio_id == patio_1.id


@pytest.mark.anyio
async def test_admin_ve_todos_los_patios(db_session):
    patio_1 = Patio(nombre="Patio Tres", codigo="RLS3")
    patio_2 = Patio(nombre="Patio Cuatro", codigo="RLS4")
    db_session.add_all([patio_1, patio_2])
    await db_session.flush()

    db_session.add_all(
        [
            Contenedor(
                numero_contenedor="CSQU3054383", tipo=TipoContenedor.LLENO, tamano=TamanoContenedor.CUARENTA,
                patio_id=patio_1.id, estado=EstadoContenedor.SOLICITUD_INGRESO, peso_kg=18000,
            ),
            Contenedor(
                numero_contenedor="TRHU1866154", tipo=TipoContenedor.LLENO, tamano=TamanoContenedor.CUARENTA,
                patio_id=patio_2.id, estado=EstadoContenedor.SOLICITUD_INGRESO, peso_kg=15000,
            ),
        ]
    )
    await db_session.commit()

    app_engine = create_async_engine(os.environ["DATABASE_URL"])
    session_factory = async_sessionmaker(app_engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as scoped_session:
        await scoped_session.execute(text("SET app.rol = :rol"), {"rol": RolUsuario.ADMIN.value})
        await scoped_session.execute(text("SET app.patios_asignados = :patios"), {"patios": ""})
        result = await scoped_session.execute(select(Contenedor))
        visibles = result.scalars().all()

    await app_engine.dispose()

    assert len(visibles) >= 2
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd backend && pytest tests/test_rls.py -v
```
Esperado: FAIL — sin RLS, `test_operador_solo_ve_contenedores_de_su_patio` ve ambos contenedores (assert `len(visibles) == 1` falla)

- [ ] **Step 3: `backend/app/alembic/versions/0006_rls_policies.py`**

```python
"""rls policies por patio_id

Revision ID: 0006_rls_policies
Revises: 0005_contenedor_movimiento
Create Date: 2026-09-14
"""
from alembic import op

revision = "0006_rls_policies"
down_revision = "0005_contenedor_movimiento"
branch_labels = None
depends_on = None

_TABLAS = ("contenedores", "movimientos", "auditoria")


def upgrade() -> None:
    for tabla in _TABLAS:
        op.execute(f"ALTER TABLE {tabla} ENABLE ROW LEVEL SECURITY;")
        op.execute(
            f"""
            CREATE POLICY {tabla}_por_patio ON {tabla}
              USING (
                current_setting('app.rol', true) = 'admin'
                OR patio_id::text = ANY(
                  string_to_array(coalesce(current_setting('app.patios_asignados', true), ''), ',')
                )
              );
            """
        )


def downgrade() -> None:
    for tabla in _TABLAS:
        op.execute(f"DROP POLICY IF EXISTS {tabla}_por_patio ON {tabla};")
        op.execute(f"ALTER TABLE {tabla} DISABLE ROW LEVEL SECURITY;")
```

- [ ] **Step 4: Agregar `get_scoped_db` en `backend/app/api/deps.py`**

Agregar al final del archivo (después de `require_roles`):

```python
from sqlalchemy import text


async def get_scoped_db(
    user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AsyncSession:
    await db.execute(text("SET LOCAL app.rol = :rol"), {"rol": user.rol.value})
    await db.execute(
        text("SET LOCAL app.patios_asignados = :patios"),
        {"patios": ",".join(str(p) for p in user.patios)},
    )
    return db
```

- [ ] **Step 5: Usar `get_scoped_db` en `obtener_contenedor` (`backend/app/api/routes/contenedores.py`)**

Reemplazar la firma de `obtener_contenedor`:

```python
from app.api.deps import CurrentUser, get_current_user, get_scoped_db, require_roles


@router.get("/{contenedor_id}", response_model=ContenedorOut)
async def obtener_contenedor(
    contenedor_id: str,
    db: AsyncSession = Depends(get_scoped_db),
    user: CurrentUser = Depends(get_current_user),
) -> Contenedor:
    result = await db.execute(select(Contenedor).where(Contenedor.id == contenedor_id))
    contenedor = result.scalar_one_or_none()
    if contenedor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado")
    return contenedor
```

- [ ] **Step 6: Correr tests, confirmar que pasan**

```bash
cd backend && pytest tests/test_rls.py -v
```
Esperado: PASS (2 tests)

- [ ] **Step 7: Correr suite completa**

```bash
cd backend && pytest -v
```
Esperado: PASS — todos los tests de Tasks 1–13.

- [ ] **Step 8: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/alembic/versions/0006_rls_policies.py backend/app/api/deps.py \
  backend/app/api/routes/contenedores.py backend/tests/test_rls.py
git commit -m "feat: RLS por patio_id en contenedores, movimientos y auditoria"
```

---

## Self-Review

**Cobertura del spec (sección relevante a esta fase):**
- Jerarquía PATIO→CARRIL→TRAMO→TIRA→NIVEL con bloqueo estricto → Tasks 3, 11 (unique constraint + check nivel 1-5 + índice único parcial de ubicación).
- Máquina de estados del contenedor → Task 6 (`EstadoContenedor`), Task 11 (transición a `UBICADO`). Estados posteriores (`EN_PORTERIA`, `DESPACHADO`, etc.) se disparan en el plan de QR/portería, no aquí.
- Roles y permisos (RBAC) → Task 4 (`RolUsuario`), Task 8 (`require_roles`).
- Auditoría completa (quién, qué, cuándo, IP/dispositivo, valor anterior/nuevo) → Task 5 (`registrar_auditoria`), usado en Tasks 9–11.
- Multi-patio por `patio_id` + RLS, un solo esquema → Task 13.
- Algoritmo de sugerencia de ubicación con scoring, restricciones duras, override manual → Task 12 (override se registra vía `score_sugerido`/`score_elegido`/`motivo_override` en Task 11, consumido desde el futuro cliente).
- Identidad que deje espacio a SSO futuro → `password_hash` nullable (Task 4); tabla `identidades_federadas` queda para el plan de auth extendida (fuera de alcance, documentado en el header).

**Placeholders:** ninguno — cada step tiene código completo, sin "TBD"/"similar a".

**Consistencia de tipos:** `registrar_auditoria` firma igual en Task 5 y usos en Tasks 9–11 (`usuario_id`, `rol`, `ip`, `dispositivo`, `accion`, `entidad`, `entidad_id`, `valor_anterior`, `valor_nuevo`, `patio_id`). `CurrentUser.rol` es `RolUsuario` en Task 8 y así se consume en Tasks 9–13. `sugerir_ubicacion` firma coincide entre Task 12 (definición) y su único consumidor (`ubicaciones.py`, mismo Task).

---

**Plan guardado en `docs/superpowers/plans/2026-09-14-backend-foundation.md`.**
