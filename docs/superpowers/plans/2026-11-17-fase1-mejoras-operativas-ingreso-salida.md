# Fase 1: Mejoras Operativas - Ingreso Rápido y Salida Controlada Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Phase 1 backend endpoints, migrations, and frontend components for fast container entry verification/PIN capture with required inspection/photos, crane operator assignment, and validated exit workflow.

**Architecture:** Extend FastAPI backend with transactional endpoints for porteria entries, inspection logging to DigitalOcean Spaces via signed URLs, unique partial index on active container numbers, and mobile-first frontend views for guards and crane operators.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Next.js, React, Tailwind CSS, Vitest, Pytest.

## Global Constraints

- No UUIDs in user forms or fields.
- ISO 6346 container number validation on input.
- Zero open-ended placeholders ("TODO", "TBD").
- TDD approach: write tests first, verify failure, implement, verify pass, commit.
- Role checks: `guardia` for porteria, `operador_grua` for yard placement, `despachador` for gate exit.

---

### Task 1: Database Migration and Models for Inspections and Evidences

**Files:**
- Create: `backend/alembic/versions/0012_inspecciones_y_evidencias.py` (or next migration number)
- Modify: `backend/app/models/__init__.py`, `backend/app/models/contenedor.py`, `backend/app/models/movimiento.py`
- Test: `backend/tests/test_fase1_migraciones.py`

**Interfaces:**
- Consumes: Existing DB session and base models.
- Produces: `Inspeccion` model, `Evidencia` model, partial unique index on `numero_contenedor` for active states.

- [ ] **Step 1: Write failing test for migration and models**

```python
import pytest
from sqlalchemy.exc import IntegrityError
from app.models.contenedor import Contenedor, EstadoContenedor
from app.models.inspeccion import Inspeccion
from app.models.evidencia import Evidencia

@pytest.mark.asyncio
async def test_contenedor_active_unique_index(db_session):
    c1 = Contenedor(numero_contenedor="MSCU1234567", patio_id=1, cliente_id=1, estado=EstadoContenedor.ingresado)
    db_session.add(c1)
    await db_session.commit()
    
    c2 = Contenedor(numero_contenedor="MSCU1234567", patio_id=1, cliente_id=2, estado=EstadoContenedor.ingresado)
    db_session.add(c2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_fase1_migraciones.py -v`
Expected: FAIL with table/column/index not found error

- [ ] **Step 3: Implement models and Alembic migration**

Create `backend/app/models/inspeccion.py`, `backend/app/models/evidencia.py`, update `backend/app/models/__init__.py`, and generate/write the Alembic migration script.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_fase1_migraciones.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/ backend/app/models/ backend/tests/test_fase1_migraciones.py
git commit -m "feat(fase1): add inspecciones and evidencias models with unique active container index"
```

---

### Task 2: Porteria Entry Endpoint with PIN Verification and Photos

**Files:**
- Create: `backend/app/schemas/porteria.py`, `backend/app/api/porteria.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_fase1_porteria.py`

**Interfaces:**
- Consumes: `Inspeccion`, `Evidencia`, `Contenedor` models.
- Produces: `POST /api/porteria/ingresos`, `GET /api/porteria/buscar`.

- [ ] **Step 1: Write failing test for porteria entry endpoint**

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_porteria_ingreso_requires_photos(client: AsyncClient, token_guardia):
    response = await client.post(
        "/api/porteria/ingresos",
        json={"pin": "123456", "placas": "ABC-123", "operador": "Juan", "sellos": "S1", "evidencias": []},
        headers={"Authorization": f"Bearer {token_guardia}"}
    )
    assert response.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_fase1_porteria.py -v`
Expected: FAIL with 404 or 405

- [ ] **Step 3: Implement schemas and porteria router**

Write `backend/app/schemas/porteria.py` and `backend/app/api/porteria.py` enforcing PIN validation, mandatory photos, inspection records, and returning location suggestions.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_fase1_porteria.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/porteria.py backend/app/api/porteria.py backend/tests/test_fase1_porteria.py backend/app/main.py
git commit -m "feat(fase1): add porteria entry api with pin validation and mandatory photos"
```

---

### Task 3: Crane Operator & Validated Exit Backend Rules

**Files:**
- Create: `backend/app/api/salidas.py`, `backend/app/api/ubicacion_grua.py`
- Modify: `backend/app/api/movimientos.py`
- Test: `backend/tests/test_fase1_salidas_grua.py`

**Interfaces:**
- Consumes: Container state machine (`ubicado` -> `solicitud_salida` -> `en_porteria_salida` -> `despachado`).
- Produces: `POST /api/contenedores/{id}/ubicar`, `POST /api/contenedores/{id}/despachar`.

- [ ] **Step 1: Write failing test for validated exit rule**

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_dispatch_rejects_non_gate_ready_container(client: AsyncClient, token_despachador):
    response = await client.post(
        "/api/contenedores/1/despachar",
        json={"pin_salida": "999999"},
        headers={"Authorization": f"Bearer {token_despachador}"}
    )
    assert response.status_code == 409
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_fase1_salidas_grua.py -v`
Expected: FAIL

- [ ] **Step 3: Implement dispatch and crane operator placement endpoints**

Add backend logic checking that only `en_porteria_salida` containers can be dispatched, and crane operators can confirm placement from `ingresado` to `ubicado`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_fase1_salidas_grua.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/salidas.py backend/app/api/ubicacion_grua.py backend/tests/test_fase1_salidas_grua.py
git commit -m "feat(fase1): add validated exit and crane operator placement endpoints"
```
