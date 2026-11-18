# Fase 2: Ubicación de Contenedores y Mapa del Patio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Phase 2 global search (`/api/buscar`), cascaded pickers (`ContenedorPicker`, `UbicacionPicker`), re-location endpoint with stacking rules (no floating positions, max height, top-container-only unstacking), remanejos calculation, and map color mode extensions.

**Architecture:** Implement backend search index with `text_pattern_ops`, strict placement validation rules in SQLAlchemy transactions, and React components supporting Ctrl+K global search and map color filters.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Alembic, Next.js, React, Tailwind CSS, Vitest, Pytest.

## Global Constraints

- No UUIDs in user forms or fields.
- Short human-readable labels (`A01-T04-R02-N1`) and long labels (`Carril A01 · Tramo T04 · Tira R02 · Nivel 1`).
- Zero open-ended placeholders ("TODO", "TBD").
- TDD approach: write tests first, verify failure, implement, verify pass, commit.

---

### Task 1: Global Search and Readable Location Labels

**Files:**
- Create: `backend/app/core/ubicaciones.py`, `backend/app/api/buscar.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_fase2_buscar.py`

**Interfaces:**
- Consumes: Container and location tables.
- Produces: `GET /api/buscar?q=&patio_id=`, `etiqueta_ubicacion(ubicacion)`.

- [ ] **Step 1: Write failing test for global search and short labels**

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_global_search_requires_minimum_characters(client: AsyncClient, token_admin):
    response = await client.get("/api/buscar?q=MSC", headers={"Authorization": f"Bearer {token_admin}"})
    assert response.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_fase2_buscar.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `etiqueta_ubicacion` and search endpoint**

Create `backend/app/core/ubicaciones.py` with short and long formatters, and `backend/app/api/buscar.py` enforcing min 4 chars and prefix/contains index lookup.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_fase2_buscar.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/ubicaciones.py backend/app/api/buscar.py backend/tests/test_fase2_buscar.py backend/app/main.py
git commit -m "feat(fase2): add global search endpoint and readable location label helpers"
```

---

### Task 2: Stacking Rules and Re-location Endpoint

**Files:**
- Create: `backend/app/api/reubicar.py`
- Modify: `backend/app/models/tira.py` (add `max_niveles`)
- Test: `backend/tests/test_fase2_estiba.py`

**Interfaces:**
- Consumes: Location slots, stacking height limits, container stack hierarchy.
- Produces: `POST /api/contenedores/{id}/reubicar` enforcing 409 on floating positions or unstacking violations.

- [ ] **Step 1: Write failing test for floating position validation**

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_ubicacion_floating_position_rejected(client: AsyncClient, token_operador_grua):
    response = await client.post(
        "/api/contenedores/1/reubicar",
        json={"ubicacion_destino_id": 99, "motivo": "Reubicacion de prueba"},
        headers={"Authorization": f"Bearer {token_operador_grua}"}
    )
    assert response.status_code in (400, 409, 422)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_fase2_estiba.py -v`
Expected: FAIL

- [ ] **Step 3: Implement re-location validation rules**

Add transaction checks in `backend/app/api/reubicar.py` ensuring level n-1 is occupied before placing at level n, max height is respected, and containers underneath cannot be bypassed.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_fase2_estiba.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/reubicar.py backend/tests/test_fase2_estiba.py backend/app/models/tira.py
git commit -m "feat(fase2): add relocation api with strict stacking rules and remanejos count"
```

---

### Task 3: Map Color Modes and Frontend Pickers

**Files:**
- Create: `frontend/components/ui/ContenedorPicker.tsx`, `frontend/components/ui/UbicacionPicker.tsx`, `frontend/components/BuscadorGlobal.tsx`
- Modify: `frontend/app/mapa/page.tsx`
- Test: `frontend/tests/ubicacion_pickers.test.tsx`

**Interfaces:**
- Consumes: `/api/buscar`, `/api/patios/{id}/mapa?modo=`.
- Produces: Interactive map color mode switching, Ctrl+K global search modal, combobox pickers.

- [ ] **Step 1: Write failing test for pickers and map color modes**

```tsx
import { render, screen } from '@testing-library/react';
import { UbicacionPicker } from '@/components/ui/UbicacionPicker';

test('UbicacionPicker renders suggestions first', () => {
  render(<UbicacionPicker patioId={1} onSelect={() => {}} />);
  expect(screen.getByText(/sugerencias/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run frontend/tests/ubicacion_pickers.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement pickers, global search dialog, and map color modes**

Build `ContenedorPicker`, `UbicacionPicker`, `BuscadorGlobal`, and update `/mapa` to support color modes (client, days, empty/full, pending service).

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run frontend/tests/ubicacion_pickers.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/components/ui/ContenedorPicker.tsx frontend/components/ui/UbicacionPicker.tsx frontend/components/BuscadorGlobal.tsx frontend/app/mapa/page.tsx frontend/tests/ubicacion_pickers.test.tsx
git commit -m "feat(fase2): add frontend pickers, global search modal, and map color modes"
```
