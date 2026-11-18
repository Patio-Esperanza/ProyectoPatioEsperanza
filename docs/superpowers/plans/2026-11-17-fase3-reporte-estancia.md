# Fase 3: Reporte de Estancia por Día e Inventario Histórico Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Phase 3 stay calculation view (`v_estancias`), daily inventory snapshots (`inventario_diario`), timezone handling (`America/Mexico_City`), client free days (`dias_libres`), nightly snapshot cron job (`AsyncIOScheduler`), and three new report types (`inventory-at-date`, `stay-by-client`, `daily-summary`).

**Architecture:** Database view for deterministic stay calculation, robust nightly snapshot job running idempotently at 00:10 local time, and extension of the existing reports module (`reportes.py`, Excel institutional format).

**Tech Stack:** Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL, APScheduler, Vitest, Pytest.

## Global Constraints

- Day 1 counting rule: entrance day counts as day 1.
- Timezone conversion to patio local time before day extraction.
- Zero open-ended placeholders ("TODO", "TBD").
- TDD approach: write tests first, verify failure, implement, verify pass, commit.

---

### Task 1: Database Migration for Stay Fields, View `v_estancias`, and Table `inventario_diario`

**Files:**
- Create: `backend/alembic/versions/0013_v_estancias_e_inventario_diario.py`
- Modify: `backend/app/models/patio.py`, `backend/app/models/cliente.py`, `backend/app/models/contenedor.py`
- Test: `backend/tests/test_fase3_estancias.py`

**Interfaces:**
- Consumes: Contenedor, Movimiento, Cliente, Patio models.
- Produces: `v_estancias` SQL view, `inventario_diario` table, `zona_horaria` and `dias_libres` columns.

- [ ] **Step 1: Write failing test for stay calculation logic**

```python
import pytest
from datetime import datetime, timezone
from app.core.estancias import calcular_dias_estancia

def test_calculo_dias_estancia_mismo_dia():
    ingreso = datetime(2026, 11, 3, 7, 0, tzinfo=timezone.utc)
    salida = datetime(2026, 11, 3, 18, 0, tzinfo=timezone.utc)
    dias = calcular_dias_estancia(ingreso, salida, "America/Mexico_City")
    assert dias == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_fase3_estancias.py -v`
Expected: FAIL

- [ ] **Step 3: Implement migration, view, and calculation helper**

Write Alembic migration 0013 creating `v_estancias` and `inventario_diario`, update models, and implement `calcular_dias_estancia` in `backend/app/core/estancias.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_fase3_estancias.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/ backend/app/models/ backend/app/core/estancias.py backend/tests/test_fase3_estancias.py
git commit -m "feat(fase3): add v_estancias view, inventario_diario table, and stay calculation logic"
```

---

### Task 2: Nightly Snapshot Job and CLI Command

**Files:**
- Create: `backend/app/jobs/corte_diario.py`, `backend/app/scheduler.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_fase3_corte.py`

**Interfaces:**
- Consumes: Movimientos, v_estancias.
- Produces: Idempotent nightly inventory snapshot job at 00:10 local time and CLI runner (`python -m app.jobs.corte_diario`).

- [ ] **Step 1: Write failing test for idempotent daily snapshot**

```python
import pytest
from app.jobs.corte_diario import ejecutar_corte_diario

@pytest.mark.asyncio
async def test_corte_diario_es_idempotente(db_session):
    fecha = "2026-11-03"
    await ejecutar_corte_diario(db_session, fecha)
    await ejecutar_corte_diario(db_session, fecha) # Should not raise integrity error
    assert True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_fase3_corte.py -v`
Expected: FAIL

- [ ] **Step 3: Implement daily snapshot job and scheduler integration**

Create `backend/app/jobs/corte_diario.py` to rebuild inventory from movements at 23:59:59 and wire APScheduler in `backend/app/scheduler.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_fase3_corte.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/jobs/corte_diario.py backend/app/scheduler.py backend/tests/test_fase3_corte.py
git commit -m "feat(fase3): add idempotent daily inventory snapshot job and scheduler"
```

---

### Task 3: New Report Types (`inventory-at-date`, `stay-by-client`, `daily-summary`)

**Files:**
- Modify: `backend/app/services/reportes_datos.py`, `backend/app/schemas/reportes.py`, `backend/app/services/reportes_excel.py`
- Test: `backend/tests/test_fase3_reportes.py`

**Interfaces:**
- Consumes: `inventario_diario`, `v_estancias`.
- Produces: Three new report types in `/api/reportes/` with Excel institutional export.

- [ ] **Step 1: Write failing test for stay report data service**

```python
import pytest
from app.services.reportes_datos import obtener_datos_reporte

@pytest.mark.asyncio
async def test_reporte_estancia_cliente_scoping(db_session):
    # Test client scoping for stay-by-client report
    datos = await obtener_datos_reporte(db_session, "stay-by-client", cliente_id=1)
    assert isinstance(datos, list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_fase3_reportes.py -v`
Expected: FAIL

- [ ] **Step 3: Implement report types and Excel generators**

Extend `reportes_datos.py`, `reportes.py` schemas, and `reportes_excel.py` to support `inventory-at-date`, `stay-by-client`, and `daily-summary`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_fase3_reportes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/reportes_datos.py backend/app/schemas/reportes.py backend/app/services/reportes_excel.py backend/tests/test_fase3_reportes.py
git commit -m "feat(fase3): add inventory-at-date, stay-by-client, and daily-summary reports with Excel export"
```
