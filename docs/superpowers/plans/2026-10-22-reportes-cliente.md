# Módulo de Reportes para Clientes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the client self-management reports module allowing clients to view container reports on screen, filter by their own containers (`cliente_id`), and export to Excel or PDF.

**Architecture:** Extend backend report endpoints to permit `RolUsuario.CLIENTE` and automatically filter query results by `user.cliente_id`. Update frontend report views and navigation so client users can access `/reportes`, view KPIs/paginated data tables, export to Excel, and export to PDF via browser print with custom print styles.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Next.js, TypeScript, Tailwind CSS, openpyxl.

## Global Constraints
- Client users can only access data belonging to their assigned `cliente_id`.
- Export to Excel uses existing `openpyxl` backend generator.
- Export to PDF uses browser-native print (`window.print()`) with print CSS.
- Match existing design system and UI components (`CatalogoReportes`, `FiltrosReporteBar`, `ResumenKpisReporte`, `TablaPreviewReporte`).

---

### Task 1: Backend API & Data Layer Updates for Client Reports

**Files:**
- Modify: `backend/app/api/routes/reportes.py`
- Modify: `backend/app/services/reportes_datos.py`
- Test: `backend/tests/test_api_reportes.py`

**Interfaces:**
- Consumes: `CurrentUser`, `RolUsuario`, `obtener_preview_reporte`
- Produces: Endpoints `/reportes/{tipo}/preview` and `/reportes/{tipo}/exportar` accessible by `RolUsuario.CLIENTE`, filtering automatically by `user.cliente_id`.

- [ ] **Step 1: Write failing test in `backend/tests/test_api_reportes.py` for client report access and scoping**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Update `backend/app/api/routes/reportes.py` and `backend/app/services/reportes_datos.py` to allow `RolUsuario.CLIENTE` and filter by `cliente_id`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/reportes.py backend/app/services/reportes_datos.py backend/tests/test_api_reportes.py
git commit -m "feat(reportes): allow client role and scope queries by cliente_id"
```

---

### Task 2: Frontend Routing & Navigation for Client Reports

**Files:**
- Modify: `frontend/lib/rutas.ts`
- Modify: `frontend/components/Sidebar.tsx`
- Modify: `frontend/app/reportes/page.tsx`

**Interfaces:**
- Consumes: `ROLES_POR_RUTA`, `Sidebar`, `RolUsuario`
- Produces: Client role permission for `/reportes` route and adjusted filter bar for clients.

- [ ] **Step 1: Update `frontend/lib/rutas.ts` to include `RolUsuario.CLIENTE` in `/reportes` route roles**
- [ ] **Step 2: Update `frontend/components/Sidebar.tsx` to show "Reportes" link for client users**
- [ ] **Step 3: Update `frontend/app/reportes/page.tsx` and filter bar to hide/adapt staff-only filters (e.g. global client selector) when viewed by a client**
- [ ] **Step 4: Commit**

```bash
git add frontend/lib/rutas.ts frontend/components/Sidebar.tsx frontend/app/reportes/ page.tsx frontend/components/reportes/
git commit -m "feat(frontend): enable reportes route and sidebar link for client users"
```

---

### Task 3: PDF Export (Browser Print) & Excel Export Integration

**Files:**
- Modify: `frontend/components/reportes/FiltrosReporteBar.tsx`
- Modify: `frontend/app/reportes/page.tsx`
- Create/Modify: CSS print styles (`frontend/app/globals.css` or module CSS)

**Interfaces:**
- Consumes: Report preview data, Excel export endpoint
- Produces: PDF export button triggering `window.print()` with clean print layout.

- [ ] **Step 1: Add "Exportar a PDF" button to `FiltrosReporteBar.tsx` / `page.tsx`**
- [ ] **Step 2: Add print CSS rules (`@media print`) to hide navigation sidebar, filter bars, and export buttons, formatting data table cleanly**
- [ ] **Step 3: Verify Excel and PDF export flows**
- [ ] **Step 4: Commit**

```bash
git add frontend/components/reportes/FiltrosReporteBar.tsx frontend/app/reportes/page.tsx frontend/app/globals.css
git commit -m "feat(reportes): add PDF export via browser print and print styles"
```

---

### Task 4: Test Suite Verification

**Files:**
- Test: `backend/tests/`

**Interfaces:**
- Consumes: All backend tests
- Produces: 100% passing test suite including new client report isolation tests.

- [ ] **Step 1: Run pytest backend test suite**
- [ ] **Step 2: Run frontend build and typecheck**
- [ ] **Step 3: Commit final verification**

```bash
git add .
git commit -m "test(reportes): verify full backend test suite and frontend build for client reports"
```
