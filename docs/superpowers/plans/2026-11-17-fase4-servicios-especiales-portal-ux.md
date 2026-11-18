# Fase 4: Servicios Especiales y Portal UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Phase 4 special services catalog, service orders lifecycle (`solicitado`, `programado`, `en_proceso`, `terminado`, `rechazado`, `cancelado`), transloading second unit capture, mandatory photo evidences, exit blocking rules, new `cuadrilla` role and screen ("Servicios de hoy"), and customer portal / admin dashboard integration.

**Architecture:** Extend FastAPI backend with service order management endpoints, Spaces signed URL evidence uploads, strict dispatch blocking checks, and mobile/desktop views for cuadrilla and admin dashboard.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Alembic, Next.js, React, Tailwind CSS, Vitest, Pytest.

## Global Constraints

- Services with `bloquea_salida=true` prevent container dispatch while pending/in-progress.
- Mandatory photo evidence when catalogue requires it.
- Zero open-ended placeholders ("TODO", "TBD").
- TDD approach: write tests first, verify failure, implement, verify pass, commit.

---

### Task 1: Database Migration for Special Services and Catalog

**Files:**
- Create: `backend/alembic/versions/0014_servicios_especiales.py`
- Modify: `backend/app/models/__init__.py`, `backend/app/models/servicio.py`
- Test: `backend/tests/test_fase4_servicios.py`

**Interfaces:**
- Consumes: Contenedor, Cliente, Evidencia models.
- Produces: `servicios_catalogo`, `servicios_contenedor` tables, initial catalogue seed (`TRA`, `REA`, `DES`, `EMP`).

- [ ] **Step 1: Write failing test for service order creation and catalog seed**

```python
import pytest
from app.models.servicio import ServicioCatalogo

@pytest.mark.asyncio
async def test_servicios_catalogo_seed_exists(db_session):
    # Verify TRA (Traspaleo), REA, DES, EMP exist
    result = await db_session.execute(select(ServicioCatalogo).where(ServicioCatalogo.codigo == "TRA"))
    servicio = result.scalar_one_or_none()
    assert servicio is not None
    assert servicio.bloquea_salida is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_fase4_servicios.py -v`
Expected: FAIL

- [ ] **Step 3: Implement migration and models for special services**

Write Alembic migration 0014 creating tables and seeding initial services (`TRA`, `REA`, `DES`, `EMP`), and implement SQLAlchemy models in `backend/app/models/servicio.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_fase4_servicios.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/ backend/app/models/servicios.py backend/tests/test_fase4_servicios.py
git commit -m "feat(fase4): add servicios_catalogo and servicios_contenedor tables with initial seed"
```

---

### Task 2: Service Order Lifecycle API and Exit Blocking Rules

**Files:**
- Create: `backend/app/schemas/servicio.py`, `backend/app/api/servicios.py`
- Modify: `backend/app/main.py`, `backend/app/api/salidas.py` (add exit blocking check)
- Test: `backend/tests/test_fase4_lifecycle.py`

**Interfaces:**
- Consumes: `servicios_contenedor`, `servicios_catalogo`.
- Produces: Service order state transition endpoints (`/programar`, `/iniciar`, `/terminar`, `/rechazar`, `/cancelar`) and dispatch blocking validation.

- [ ] **Step 1: Write failing test for service blocking container exit**

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_service_blocks_container_dispatch(client: AsyncClient, token_despachador):
    response = await client.post(
        "/api/contenedores/1/despachar",
        json={"pin_salida": "123456"},
        headers={"Authorization": f"Bearer {token_despachador}"}
    )
    assert response.status_code == 409
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_fase4_lifecycle.py -v`
Expected: FAIL

- [ ] **Step 3: Implement lifecycle endpoints and exit blocking logic**

Write `backend/app/api/servicios.py` and update dispatch validation to reject exit when any blocking service order is not terminated.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_fase4_lifecycle.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/servicio.py backend/app/api/servicios.py backend/tests/test_fase4_lifecycle.py backend/app/api/salidas.py
git commit -m "feat(fase4): add service order lifecycle api, evidence upload, and exit blocking rules"
```

---

### Task 3: Cuadrilla Role, "Servicios de hoy" UI, and Portal Integration

**Files:**
- Create: `frontend/app/servicios/page.tsx`, `frontend/components/PanelCuadrilla.tsx`
- Modify: `frontend/lib/rutas.ts`, `frontend/components/Sidebar.tsx`
- Test: `frontend/tests/servicios_cuadrilla.test.tsx`

**Interfaces:**
- Consumes: `/api/servicios`, `/api/servicios/{id}/iniciar`, `/api/servicios/{id}/terminar`.
- Produces: Cuadrilla start/finish workflow interface, photo capture integration, and portal service request view.

- [ ] **Step 1: Write failing test for cuadrilla view**

```tsx
import { render, screen } from '@testing-library/react';
import ServiciosPage from '@/app/servicios/page';

test('ServiciosPage renders today services list', () => {
  render(<ServiciosPage />);
  expect(screen.getByText(/servicios de hoy/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run frontend/tests/servicios_cuadrilla.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement cuadrilla view and portal service components**

Build `ServiciosPage`, `PanelCuadrilla`, and update route permissions and sidebar for `cuadrilla` and `operador_grua` roles.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run frontend/tests/servicios_cuadrilla.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/app/servicios/page.tsx frontend/components/PanelCuadrilla.tsx frontend/lib/rutas.ts frontend/components/Sidebar.tsx frontend/tests/servicios_cuadrilla.test.tsx
git commit -m "feat(fase4): add cuadrilla services view, role routing, and portal integration"
```
