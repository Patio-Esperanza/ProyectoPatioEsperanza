# API de socios: solicitud de entrada desde el transportista (Kasu) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement API for external partners (Kasu) to submit container entry requests, authenticate via API key, manage entry request lifecycle (PATCH, cancel), support multi-yard permissions, auto-create clients with `alta_por_socio = true`, and deliver webhooks back to partners with HMAC signatures.

**Architecture:** Add `credenciales_socio` and `eventos_socio` tables, extend `contenedores` and `clientes` schemas, create secure API key dependency (`get_socio`), implement `/api/socios/v1/solicitudes-ingreso` endpoints, update portería search to show expected transport, and configure background webhook dispatch.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, PostgreSQL, pytest.

## Global Constraints

- Python 3.12 / FastAPI / SQLAlchemy async/sync models matching existing codebase patterns.
- Authentication via `Authorization: ApiKey <prefijo>.<secreto>` using bcrypt hashes.
- Idempotency key per partner credential.
- Strict test coverage for all endpoints and error cases (401, 403, 409).

---

### Task 1: Database Migration & Models for Partners, Events, and Container Extensions

**Files:**
- Create: `backend/app/alembic/versions/0020_api_socios.py`
- Modify: `backend/app/models/contenedor.py`, `backend/app/models/cliente.py`
- Create: `backend/app/models/socio.py`
- Test: `backend/tests/test_api_socios_models.py`

**Interfaces:**
- Consumes: Existing DB session and models.
- Produces: `CredencialSocio`, `EventoSocio` models, and updated `Contenedor` / `Cliente` fields.

- [ ] **Step 1: Write failing test for partner credential and container new columns**

```python
import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.socio import CredencialSocio, EventoSocio
from app.models.contenedor import Contenedor
from app.models.cliente import Cliente

@pytest.mark.asyncio
async def test_credencial_socio_model(db_session: AsyncSession):
    socio = CredencialSocio(
        nombre="Kasu",
        prefijo="kasu0001",
        secreto_hash="hash",
        patios_permitidos=[uuid4()],
        activo=True
    )
    db_session.add(socio)
    await db_session.commit()
    assert socio.id is not None
    assert socio.prefijo == "kasu0001"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_api_socios_models.py -v`
Expected: FAIL with `ModuleNotFoundError` or table missing.

- [ ] **Step 3: Implement models and Alembic migration**

Create `backend/app/models/socio.py`:
```python
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.sql import func
from app.db import Base

class CredencialSocio(Base):
    __tablename__ = "credenciales_socio"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(100), nullable=False)
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=True)
    prefijo = Column(String(8), unique=True, nullable=False, index=True)
    secreto_hash = Column(String(255), nullable=False)
    patios_permitidos = Column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)
    webhook_url = Column(String(500), nullable=True)
    webhook_secreto = Column(String(255), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    ultimo_uso_en = Column(DateTime(timezone=True), nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

class EventoSocio(Base):
    __tablename__ = "eventos_socio"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    credencial_socio_id = Column(UUID(as_uuid=True), ForeignKey("credenciales_socio.id"), nullable=False)
    contenedor_id = Column(UUID(as_uuid=True), ForeignKey("contenedores.id"), nullable=False)
    tipo = Column(String(50), nullable=False)
    payload = Column(JSONB, nullable=False)
    estado = Column(String(20), nullable=False, default="pendiente") # pendiente, enviado, fallido
    intentos = Column(Integer, nullable=False, default=0)
    siguiente_intento_en = Column(DateTime(timezone=True), server_default=func.now())
    ultimo_error = Column(Text, nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
```

Update `backend/app/models/contenedor.py` and `backend/app/models/cliente.py` with new columns:
- `origen`, `credencial_socio_id`, `idempotency_key`, `referencia_externa`, `datos_aduana`, `transporte_esperado`, `peso_por_confirmar` in `contenedores`.
- `alta_por_socio` in `clientes`.
- Unique constraint on `(credencial_socio_id, idempotency_key)` where `idempotency_key IS NOT NULL`.

Create migration `backend/app/alembic/versions/0020_api_socios.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_api_socios_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/socio.py backend/app/models/contenedor.py backend/app/models/cliente.py backend/app/alembic/versions/
git commit -m "feat(socios): add credenciales_socio, eventos_socio and model extensions"
```

---

### Task 2: Security & Dependency `get_socio` with API Key Authentication

**Files:**
- Create: `backend/app/core/socio_security.py`
- Modify: `backend/app/api/deps.py`
- Test: `backend/tests/test_socio_security.py`

**Interfaces:**
- Consumes: `CredencialSocio` model.
- Produces: `get_socio` FastAPI dependency.

- [ ] **Step 1: Write failing test for `get_socio`**

```python
import pytest
from fastapi import HTTPException
from app.core.socio_security import verificar_api_key

@pytest.mark.asyncio
async def test_verificar_api_key_invalid():
    with pytest.raises(HTTPException) as exc:
        await verificar_api_key("ApiKey invalid.key")
    assert exc.value.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_socio_security.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement API key verification and RLS GUC context**

Create `backend/app/core/socio_security.py`:
- Parse `ApiKey <prefijo>.<secreto>`
- Query active `CredencialSocio` by `prefijo`
- Verify `secreto` against `secreto_hash` using bcrypt / passlib
- Set RLS context (`app.rol = 'socio'`, `app.patios_asignados = patios_permitidos`)
- Update `ultimo_uso_en`

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_socio_security.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/socio_security.py backend/tests/test_socio_security.py
git commit -m "feat(socios): implement API key authentication dependency and RLS setup"
```

---

### Task 3: Client Auto-Creation & Request Validation

**Files:**
- Create: `backend/app/services/socio_service.py`
- Test: `backend/tests/test_socio_service.py`

**Interfaces:**
- Consumes: `Cliente`, `Contenedor` models.
- Produces: `resolver_o_crear_cliente` service function.

- [ ] **Step 1: Write failing test for client auto-creation**

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.socio_service import resolver_o_crear_cliente
from app.models.enums import TipoCliente

@pytest.mark.asyncio
async def test_crear_cliente_nuevo_por_socio(db_session: AsyncSession):
    cliente = await resolver_o_crear_cliente(
        db_session,
        tipo=TipoCliente.IMPORTADOR_EXPORTADOR,
        rfc="IMM210702NL7",
        nombre="Importadora X"
    )
    assert cliente.id is not None
    assert cliente.alta_por_socio is True
    assert cliente.dias_libres == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_socio_service.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `socio_service.py`**

Implement client resolution by RFC (creates with `alta_por_socio = true`, `dias_libres = 0` if not exists, supports `naviera`, `agencia_aduanal`, `importador_exportador`), container number ISO 6346 validation, and duplication handling (`IntegrityError` -> 409).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_socio_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/socio_service.py backend/tests/test_socio_service.py
git commit -m "feat(socios): implement client auto-creation and request validation service"
```

---

### Task 4: Endpoints (`POST`, `PATCH`, `CANCEL`, `GET`) & Portería Transport Integration

**Files:**
- Create: `backend/app/api/routes/socios.py`
- Modify: `backend/app/api/porteria.py`, `backend/app/main.py`
- Test: `backend/tests/test_api_socios.py`

**Interfaces:**
- Consumes: `get_socio`, `resolver_o_crear_cliente`.
- Produces: `/api/socios/v1/solicitudes-ingreso` endpoints and portería expected transport display & `placas_coinciden` check.

- [ ] **Step 1: Write failing test for `POST /api/socios/v1/solicitudes-ingreso`**

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_crear_solicitud_ingreso_socio(async_client: AsyncClient, socio_auth_headers):
    payload = {
        "idempotency_key": "kasu:123",
        "referencia_externa": "REF-001",
        "patio_id": "...",
        "numero_contenedor": "MSCU1234567",
        "tipo": "lleno",
        "tamano": "40",
        "tipo_iso": "40HC",
        "peso_kg": 18500,
        "cliente": {"tipo": "importador_exportador", "rfc": "IMM210702NL7", "nombre": "Importadora X"},
        "aduana": {"agencia": "LOGINCO", "num_refe": "LCLF0353/26"},
        "transporte": {"operador": "Juan Pérez", "telefono": "3311223344", "placas": "12AB3C", "numero_economico": "21"},
        "fecha_estimada_llegada": "2026-11-25T09:00:00-06:00"
    }
    response = await async_client.post("/api/socios/v1/solicitudes-ingreso", json=payload, headers=socio_auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert "pin" in data
    assert data["estado"] == "solicitud_ingreso"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_api_socios.py -v`
Expected: FAIL with 404/500.

- [ ] **Step 3: Implement socios router and porteria enhancements**

Implement:
- `POST /api/socios/v1/solicitudes-ingreso` (idempotency, patio check, PIN generation, container creation).
- `PATCH /api/socios/v1/solicitudes-ingreso/{id}` (update transport & ETA in `solicitud_ingreso` only).
- `POST /api/socios/v1/solicitudes-ingreso/{id}/cancelar` (reject if in `solicitud_ingreso`).
- `GET /api/socios/v1/contenedores/{id}`.
- Update Portería search & ingreso to return `transporte_esperado` and store `placas_coinciden`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_api_socios.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/socios.py backend/app/api/porteria.py backend/app/main.py backend/tests/test_api_socios.py
git commit -m "feat(socios): implement partner request REST API and porteria transport integration"
```

---

### Task 5: Webhook Outbox & Scheduler Dispatch

**Files:**
- Create: `backend/app/jobs/webhooks_socio.py`
- Modify: `backend/app/scheduler.py`, portería ingresos/salidas actions.
- Test: `backend/tests/test_webhooks_socio.py`

**Interfaces:**
- Consumes: `EventoSocio`, `CredencialSocio`.
- Produces: Webhook outbox insertion on state change (`contenedor.ingresado`, `contenedor.rechazado`, `contenedor.despachado`) and background dispatcher job.

- [ ] **Step 1: Write failing test for webhook outbox insertion and HMAC signature**

```python
import pytest
from app.jobs.webhooks_socio import generar_firma_hmac

def test_generar_firma_hmac():
    firma = generar_firma_hmac(b"payload", "secreto")
    assert firma.startswith("sha256=")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_webhooks_socio.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement webhook dispatcher and event triggers**

Implement:
- Outbox insertion in same transaction as container state changes (`ingresado`, `rechazado`, `despachado`).
- Background job in `app/scheduler.py` running every minute with HMAC signing (`X-Esperanza-Firma`, `X-Esperanza-Evento-Id`) and exponential backoff.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_webhooks_socio.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/jobs/webhooks_socio.py backend/app/scheduler.py backend/app/api/porteria.py backend/tests/test_webhooks_socio.py
git commit -m "feat(socios): implement webhook outbox system, HMAC signatures, and dispatcher scheduler"
```

---

### Task 6: CLI Script for Credential Administration & Final Verification

**Files:**
- Create: `backend/app/scripts/crear_credencial_socio.py`
- Test: Full test suite execution.

**Interfaces:**
- Consumes: DB session & bcrypt hasher.
- Produces: CLI management command for creating partner credentials and printing API keys.

- [ ] **Step 1: Implement management script**

Create `backend/app/scripts/crear_credencial_socio.py`:
- Generates 8-char prefix and secure random secret.
- Saves bcrypt hash to `credenciales_socio`.
- Prints `ApiKey <prefijo>.<secreto>` once.

- [ ] **Step 2: Run complete backend and frontend test suite**

Run: `pytest -v` and frontend tests.
Expected: ALL PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/app/scripts/crear_credencial_socio.py
git commit -m "feat(socios): add partner credential creation CLI script and verify all tests"
```
