# Plan de Implementación — Módulo Generador de Reportes y Envíos Automáticos (Preview, Excel, APScheduler)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar un módulo completo de reportes operativos ("Generador de reportes") con previsualización interactiva tabular en pantalla, exportación a archivos Excel (.xlsx) estilizados con `openpyxl` y **programación de envíos automáticos periódicos por correo electrónico vía SendGrid usando `AsyncIOScheduler` (APScheduler)**.

**Architecture:**
- **Backend:** FastAPI + SQLAlchemy 2.0 async + APScheduler + SendGrid.
  - Modelo de base de datos `ReporteProgramado` con migración Alembic.
  - Servicio `reportes_datos.py` para queries analíticas y agregaciones KPI de los 5 reportes.
  - Servicio `reportes_excel.py` para generación binaria de hojas Excel estilizadas con `openpyxl` (fuente Arial, paleta `#1F4E79`, zebra striping `#F9F9F9`, metadatos en fila 1 y 2).
  - Servicio `reportes_scheduler.py` con `AsyncIOScheduler` montado en el lifespan de FastAPI para ejecutar cron jobs, generar Excels y enviarlos como adjuntos por correo.
  - Rutas en `app/api/routes/reportes.py` con endpoints de preview JSON, exportación .xlsx, y CRUD + ejecución de pruebas para reportes programados.
- **Frontend:** Next.js 15 App Router + React 19.
  - Pantalla `/reportes` en layout maestro-detalle: catálogo lateral de reportes, barra de filtros, KPIs, tabla interactiva con `DataTable`, botón de descarga directa de Excel y modal de programación de envíos automáticos con historial de ejecuciones.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, openpyxl, APScheduler, SendGrid, Next.js 15, React 19, TypeScript, CSS Modules, pytest.

## Global Constraints

- Backend commands run from `/home/tony/Developer/ProyectoPatioEsperanza/backend` with `source .venv/bin/activate && PYTHONPATH=.` before `pytest`.
- Frontend commands run from `/home/tony/Developer/ProyectoPatioEsperanza/frontend`.
- Only staff roles (`operador`, `supervisor`, `admin`) may access the reports module.
- Excel generation must adhere strictly to the visual format and column schemas of the 5 reference files in `Ejemplo de Reportes/`.
- Commit messages must end with `Co-Authored-By: Claude Code <noreply@anthropic.com>`.

---

### Task 1: Instalar dependencias, Schemas Pydantic, Modelo ORM y Migración Alembic

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/app/schemas/reportes.py`
- Create: `backend/app/models/reporte_programado.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/alembic/versions/<timestamp>_crear_tabla_reportes_programados.py`
- Test: `backend/tests/test_schemas_reportes.py`

**Interfaces:**
- `ReporteTipo`: Enum (`containers-in-yard`, `entry-movements`, `departure-movements`, `positions`, `special-services`).
- `FrecuenciaReporte`: Enum (`diario`, `semanal`, `mensual`).
- `FiltrosReporte`: Modelo Pydantic con `fecha_inicio`, `fecha_fin`, `patio_id`, `cliente_id`, `busqueda`, `page`, `page_size`.
- `ReporteColumna`: `key`, `label`, `align` (`left` | `center` | `right`).
- `ReporteKpi`: `label`, `value`, `subtext`, `tone`.
- `ReportePreviewOut`: `tipo`, `titulo`, `subtitulo`, `total_registros`, `columnas`, `filas`, `kpis`, `page`, `page_size`, `total_paginas`.
- `ReporteProgramadoCreate`, `ReporteProgramadoUpdate`, `ReporteProgramadoOut`.
- Modelo SQLAlchemy `ReporteProgramado`: tabla `reportes_programados` con columnas `id`, `nombre`, `tipo_reporte`, `patio_id`, `cliente_id`, `frecuencia`, `hora`, `minuto`, `dia_semana`, `dia_mes`, `destinatarios` (JSON), `asunto`, `mensaje`, `activo`, `ultimo_envio`, `ultimo_estado`, `ultimo_error`, `created_at`, `updated_at`.

- [x] **Step 1: Agregar dependencias y escribir pruebas de schemas**

Agregar `openpyxl==3.1.5` y `apscheduler==3.10.4` a `backend/requirements.txt` y ejecutar `pip install openpyxl apscheduler`.

Crear `backend/tests/test_schemas_reportes.py`:
```python
import datetime
import uuid
from app.schemas.reportes import (
    FiltrosReporte,
    FrecuenciaReporte,
    ReporteColumna,
    ReporteKpi,
    ReportePreviewOut,
    ReporteProgramadoCreate,
    ReporteProgramadoOut,
    ReporteTipo,
)

def test_schemas_reportes_serializacion():
    filtros = FiltrosReporte(
        fecha_inicio=datetime.date(2026, 9, 1),
        fecha_fin=datetime.date(2026, 9, 30),
        page=1,
        page_size=25,
    )
    assert filtros.page == 1
    assert filtros.page_size == 25

    col = ReporteColumna(key="contenedor", label="Contenedor", align="center")
    kpi = ReporteKpi(label="Total", value="54", tone="info")
    preview = ReportePreviewOut(
        tipo=ReporteTipo.CONTAINERS_IN_YARD,
        titulo="Contenedores en Patio",
        subtitulo="Snapshot de contenedores activos",
        total_registros=1,
        columnas=[col],
        filas=[{"contenedor": "CSNU7862291"}],
        kpis=[kpi],
        page=1,
        page_size=25,
        total_paginas=1,
    )
    data = preview.model_dump()
    assert data["tipo"] == "containers-in-yard"
    assert len(data["columnas"]) == 1

def test_schema_reporte_programado():
    prog = ReporteProgramadoCreate(
        nombre="Envío Diario Contenedores",
        tipo_reporte=ReporteTipo.CONTAINERS_IN_YARD,
        frecuencia=FrecuenciaReporte.DIARIO,
        hora=8,
        minuto=30,
        destinatarios=["operaciones@empresa.com"],
        asunto="Reporte Diario de Contenedores en Patio",
    )
    assert prog.hora == 8
    assert prog.minuto == 30
    assert len(prog.destinatarios) == 1
```

- [x] **Step 2: Implementar app/schemas/reportes.py y app/models/reporte_programado.py**

Crear los modelos Pydantic y el modelo SQLAlchemy `ReporteProgramado`. Exportar en `app/models/__init__.py`.

- [x] **Step 3: Generar y aplicar migración Alembic**

Ejecutar en backend:
```bash
alembic revision --autogenerate -m "crear tabla reportes_programados"
alembic upgrade head
```

- [x] **Step 4: Ejecutar pruebas de schemas y modelos**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend && source .venv/bin/activate && pytest tests/test_schemas_reportes.py
```

---

### Task 2: Implementar Servicio de Consultas y Agregaciones (reportes_datos.py)

**Files:**
- Create: `backend/app/services/reportes_datos.py`
- Test: `backend/tests/test_reportes_datos.py`

**Interfaces:**
- `obtener_datos_contenedores_en_patio(db, filtros, patios_ids) -> tuple[list[dict], int, list[ReporteKpi]]`
- `obtener_datos_movimientos_entrada(db, filtros, patios_ids) -> tuple[list[dict], int, list[ReporteKpi]]`
- `obtener_datos_movimientos_salida(db, filtros, patios_ids) -> tuple[list[dict], int, list[ReporteKpi]]`
- `obtener_datos_posiciones(db, filtros, patios_ids) -> tuple[list[dict], int, list[ReporteKpi]]`
- `obtener_datos_servicios_especiales(db, filtros, patios_ids) -> tuple[list[dict], int, list[ReporteKpi]]`
- `obtener_preview_reporte(db, tipo, filtros, user) -> ReportePreviewOut`

- [x] **Step 1: Escribir pruebas unitarias del servicio de datos**

Crear `backend/tests/test_reportes_datos.py` con pruebas para cada uno de los 5 reportes, verificando filtrado por patio, rango de fechas, cálculo de estadía y métricas KPI.

- [x] **Step 2: Implementar backend/app/services/reportes_datos.py**

Implementar las consultas SQLAlchemy uniendo `Contenedor`, `Cliente`, `Patio`, `Movimiento`, `Ubicacion`, `Carril`, `Tramo`, `Tira` y `Usuario`, formateando las fechas al estándar `DD/MM/YYYY HH:MM:SS` y calculando los KPIs resumen.

- [x] **Step 3: Ejecutar pruebas del servicio de datos**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend && source .venv/bin/activate && pytest tests/test_reportes_datos.py
```

---

### Task 3: Implementar Generador de Archivos Excel con openpyxl (reportes_excel.py)

**Files:**
- Create: `backend/app/services/reportes_excel.py`
- Test: `backend/tests/test_reportes_excel.py`

**Interfaces:**
- `generar_excel_reporte(tipo: ReporteTipo, datos: list[dict], total_registros: int, subtitulo: str) -> io.BytesIO`

- [x] **Step 1: Escribir prueba unitaria verificando estructura visual del Excel**

Crear `backend/tests/test_reportes_excel.py`:
- Verificar que el archivo generado sea un workbook válido de openpyxl.
- Verificar merge de celdas en fila 1 y 2.
- Verificar estilos de encabezado (Fill `#1F4E79`, Font `#FFFFFF`, Arial 11pt Bold).
- Verificar que las filas de datos alternen colores (Zebra `#FFFFFF` / `#F9F9F9`).
- Verificar que los anchos de columna se calculen dinámicamente.

- [x] **Step 2: Implementar backend/app/services/reportes_excel.py**

Implementar el generador con clases de estilo de `openpyxl.styles` (`PatternFill`, `Font`, `Alignment`, `Border`, `Side`), aplicando las alturas de fila exactas (Fila 1: 40pt, Fila 2: 22pt, Fila 3: 12pt, Fila 4: 26pt, Filas 5+: 20pt) y guardando en un buffer `io.BytesIO`.

- [x] **Step 3: Ejecutar pruebas del generador de Excel**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend && source .venv/bin/activate && pytest tests/test_reportes_excel.py
```

---

### Task 4: Extensión de Envíos de Correo con Adjuntos y Servicio Scheduler (reportes_scheduler.py)

**Files:**
- Modify: `backend/app/core/email.py`
- Create: `backend/app/services/reportes_scheduler.py`
- Test: `backend/tests/test_reportes_scheduler.py`

**Interfaces:**
- `enviar_correo_con_adjunto(destinatarios: list[str], asunto: str, contenido_html: str, adjunto_bytes: bytes, adjunto_nombre: str) -> None`
- `iniciar_scheduler() -> None`
- `apagar_scheduler() -> None`
- `sincronizar_tareas_desde_db(db: AsyncSession) -> None`
- `programar_job_reporte(prog: ReporteProgramado) -> None`
- `remover_job_reporte(prog_id: uuid.UUID) -> None`
- `ejecutar_envio_reporte_programado(reporte_programado_id: uuid.UUID) -> None`

- [x] **Step 1: Extender core/email.py con soporte para adjuntos SendGrid**

Agregar función `enviar_correo_con_adjunto` utilizando `sendgrid.helpers.mail.Attachment`, `FileContent`, `FileName`, `FileType`, `Disposition`.

- [x] **Step 2: Escribir pruebas unitarias para reportes_scheduler.py**

Crear `backend/tests/test_reportes_scheduler.py` testeando el cálculo de triggers cron según frecuencia (diaria, semanal, mensual) y la ejecución de la tarea con simulación de email (mocking).

- [x] **Step 3: Implementar backend/app/services/reportes_scheduler.py**

Implementar `AsyncIOScheduler` singleton, sincronizador con base de datos y worker de ejecución que genera el Excel y despacha los correos actualizando `ultimo_envio` y `ultimo_estado`.

- [x] **Step 4: Ejecutar pruebas de scheduler**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend && source .venv/bin/activate && pytest tests/test_reportes_scheduler.py
```

---

### Task 5: Implementar Rutas API de Reportes y Registro en main.py

**Files:**
- Create: `backend/app/api/routes/reportes.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_api_reportes.py`

**Endpoints:**
- `GET /api/reportes/{tipo}/preview`: Devuelve `ReportePreviewOut` paginado.
- `GET /api/reportes/{tipo}/exportar`: Devuelve `StreamingResponse` con el archivo `.xlsx`.
- `GET /api/reportes/programados`: Listado de reportes programados.
- `POST /api/reportes/programados`: Crear nueva tarea programada.
- `GET /api/reportes/programados/{id}`: Detalle de tarea.
- `PATCH /api/reportes/programados/{id}`: Actualizar horario, destinatarios o estado activo.
- `DELETE /api/reportes/programados/{id}`: Eliminar tarea programada.
- `POST /api/reportes/programados/{id}/ejecutar`: Ejecutar envío de prueba inmediato.

- [x] **Step 1: Escribir pruebas de integración de los endpoints API**

Crear `backend/tests/test_api_reportes.py`:
- Verificar autenticación y restricción por rol.
- Verificar endpoints de preview y exportación Excel.
- Verificar CRUD completo de reportes programados y sincronización del scheduler.
- Verificar endpoint `/ejecutar` para envío manual inmediato.

- [x] **Step 2: Implementar backend/app/api/routes/reportes.py y actualizar main.py con lifespan**

Crear las rutas asegurando el uso de `deps.get_current_user` y `deps.require_roles`.
En `backend/app/main.py`, integrar el lifespan context manager para iniciar `reportes_scheduler.iniciar_scheduler()` en startup y `apagar_scheduler()` en shutdown. Registrar `reportes.router` con prefijo `/api/reportes`.

- [x] **Step 3: Ejecutar pruebas de API**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend && source .venv/bin/activate && pytest tests/test_api_reportes.py
```

---

### Task 6: Cliente API en Frontend y Tipado TypeScript

**Files:**
- Modify: `frontend/lib/api.ts`
- Test: `frontend/lib/api.test.ts` (colocado junto al módulo, siguiendo la convención existente del proyecto en vez de `frontend/tests/`)

- [x] **Step 1: Escribir pruebas unitarias del cliente API de reportes en frontend**

Crear pruebas para preview, descarga Excel, CRUD de programados y ejecución manual.

- [x] **Step 2: Agregar interfaces y métodos en frontend/lib/api.ts**

Definir:
- `ReporteTipo`, `FrecuenciaReporte`, `ReporteColumna`, `ReporteKpi`, `ReportePreview`, `FiltrosReportePayload`, `ReporteProgramado`, `ReporteProgramadoPayload`.
- `obtenerPreviewReporte(token, tipo, filtros): Promise<ReportePreview>`
- `descargarReporteExcel(token, tipo, filtros, nombreArchivo): Promise<void>`
- `listarReportesProgramados(token): Promise<ReporteProgramado[]>`
- `crearReporteProgramado(token, payload): Promise<ReporteProgramado>`
- `actualizarReporteProgramado(token, id, payload): Promise<ReporteProgramado>`
- `eliminarReporteProgramado(token, id): Promise<void>`
- `ejecutarReporteProgramadoManual(token, id): Promise<{ detail: string }>`

- [x] **Step 3: Verificar compilación de TypeScript en frontend**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend && npm run build
```

Nota: `npx tsc --noEmit` confirma que el código nuevo compila limpio. Queda un error preexistente no relacionado (`configurarLayoutPatio` sin importar en `api.test.ts`), fuera del alcance de esta tarea.

---

### Task 7: Componentes de UI de Reportes y Modal de Automatización

**Files:**
- Create: `frontend/components/reportes/CatalogoReportes.tsx`
- Create: `frontend/components/reportes/CatalogoReportes.module.css`
- Create: `frontend/components/reportes/FiltrosReporteBar.tsx`
- Create: `frontend/components/reportes/FiltrosReporteBar.module.css`
- Create: `frontend/components/reportes/ResumenKpisReporte.tsx`
- Create: `frontend/components/reportes/ResumenKpisReporte.module.css`
- Create: `frontend/components/reportes/TablaPreviewReporte.tsx`
- Create: `frontend/components/reportes/TablaPreviewReporte.module.css`
- Create: `frontend/components/reportes/ModalProgramarReporte.tsx`
- Create: `frontend/components/reportes/ModalProgramarReporte.module.css`
- Create: `frontend/components/reportes/PanelReportesProgramados.tsx`
- Create: `frontend/components/reportes/PanelReportesProgramados.module.css`

- [x] **Step 1: Implementar CatalogoReportes.tsx y FiltrosReporteBar.tsx**

Crear catálogo lateral interactivo con buscador y barra de filtros con botones "Descargar Excel" y "Programar Envío".

- [x] **Step 2: Implementar ResumenKpisReporte.tsx y TablaPreviewReporte.tsx**

Contenedor de tarjetas KPI y tabla interactiva con `DataTable`.

- [x] **Step 3: Implementar ModalProgramarReporte.tsx y PanelReportesProgramados.tsx**

Modal para configurar tareas de envío automático (frecuencia diaria/semanal/mensual, hora, selector múltiple de emails destinatarios, asunto) y panel lateral/pestaña para administrar tareas activas con botones "Probar envío", "Pausar" y "Eliminar".

---

### Task 8: Pantalla Principal /reportes, Rutas y Navegación

**Files:**
- Create: `frontend/app/reportes/page.tsx`
- Create: `frontend/app/reportes/page.module.css`
- Modify: `frontend/lib/rutas.ts`
- Modify: `frontend/components/Sidebar.tsx`

- [x] **Step 1: Configurar permisos de ruta y enlace de navegación**

En `frontend/lib/rutas.ts`, agregar `"/reportes": [...ROLES_STAFF]`.
En `frontend/components/Sidebar.tsx`, agregar `{ href: "/reportes", texto: "Reportes" }` en la sección Operación.

- [x] **Step 2: Implementar frontend/app/reportes/page.tsx**

Integrar el layout maestro-detalle con catálogo, filtros, KPIs, previsualización de datos, modal de programación y panel de tareas automatizadas.

- [x] **Step 3: Ejecutar build de frontend y verificar integración**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend && npm run build
```

---

### Task 9: Verificación Final y Pruebas E2E / Integradas

**Files:**
- Backend tests en `backend/tests/`
- Frontend build y type checking

- [x] **Step 1: Ejecutar suite completa de tests de backend**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend && source .venv/bin/activate && pytest
```

Resultado: 120 passed.

- [x] **Step 2: Ejecutar verificación de build en frontend**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend && npm run build
```

Resultado: build exitoso, ruta `/reportes` generada (6.44 kB).

`npx vitest run` deja 4 fallas preexistentes y ajenas a este módulo:
`lib/api.test.ts` (2, falta el import de `configurarLayoutPatio`) y
`app/ubicaciones/sugerir/page.test.tsx` (2, el formulario cambió de campos). Ningún
archivo del módulo de reportes las provoca.
