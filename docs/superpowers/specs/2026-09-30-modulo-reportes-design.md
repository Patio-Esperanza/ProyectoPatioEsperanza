# Módulo Generador de Reportes Operativos (Preview, Excel y Envíos Automáticos)

Fecha: 2026-09-30
Estado: propuesto (actualizado con envíos automáticos)

## Problema

El sistema de Patio Esperanza gestiona el ciclo de vida operativo de contenedores, movimientos de entrada/salida, asignación de posiciones y servicios especiales. Sin embargo, no existe una interfaz unificada ni endpoints dedicados para generar reportes operativos consolidados con exportación formal a Excel (.xlsx), previsualización tabular en pantalla ni **envío automático periódico por correo electrónico a destinatarios configurables**.

Los operadores, supervisores y administradores necesitan consultar métricas operativas clave, descargar hojas de cálculo formateadas con la identidad visual corporativa de Patio Esperanza (`#1F4E79`, Arial, zebra striping, metadatos) y **programar envíos automáticos (diarios, semanales, mensuales) a clientes y directivos sin intervención manual**.

## Alcance

Entra en este spec:

- Pantalla interactiva `/reportes` en Next.js con layout maestro-detalle idéntico al diseño de `PantallReportes.png`.
- Catálogo lateral de 5 reportes operativos con buscador rápido y tarjetas con badges temáticos:
  1. `Contenedores en Patio` (`CONTAINERS-IN-YARD`)
  2. `Movimientos de Entrada` (`ENTRY-MOVEMENTS`)
  3. `Movimientos de Salida` (`DEPARTURE-MOVEMENTS`)
  4. `Reporte de Posiciones` (`POSITIONS`)
  5. `Servicios Especiales` (`SPECIAL-SERVICES`)
- Panel de filtros dinámicos por reporte: rango de fechas (inicio/fin), selector de patio, selector de cliente y búsqueda de texto.
- Tira de tarjetas KPI con resumen operativo del reporte activo.
- Previsualización tabular interactiva en pantalla usando `DataTable` con paginación y ordenamiento.
- Generador de archivos Excel (.xlsx) en backend usando `openpyxl` que replica al 100% el formato, tipografía (Arial), colores de encabezado (`#1F4E79`), metadatos en fila 1 y 2, anchos de columna y zebra striping de los 5 archivos de referencia en `Ejemplo de Reportes/`.
- Endpoints en FastAPI para previsualización JSON y descarga binaria en streaming `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.
- **Motor de Envíos Automáticos con APScheduler (`AsyncIOScheduler`):**
  - Tareas en segundo plano ejecutadas dentro del ciclo de vida de FastAPI.
  - Generación del Excel en memoria y envío como adjunto vía SendGrid (`sendgrid.helpers.mail.Attachment`).
  - Sincronización dinámica de tareas al crear/modificar/eliminar programaciones.
  - Registro de auditoría del último envío (fecha, estado `exitoso`/`fallido`, mensaje de error).
- **Gestión de Reportes Programados en Base de Datos:**
  - Nueva tabla `reportes_programados` con campos para tipo de reporte, filtros predeterminados, frecuencia (diaria, semanal, mensual), hora, día, lista de destinatarios, asunto, cuerpo de correo y estado activo/inactivo.
  - Endpoints CRUD y endpoint de ejecución inmediata para pruebas (`/api/reportes/programados/{id}/ejecutar`).
- **Interfaz UI de Programación y Automatización:**
  - Vista/pestaña de gestión de envíos programados dentro de `/reportes`.
  - Formulario modal para crear y editar programaciones con validación de emails y horarios.
  - Botón de "Probar envío ahora" para validación inmediata.
- Integración de permisos basada en roles (`operador`, `supervisor`, `admin`) con aislamiento RLS por patio.
- Registro en `frontend/lib/rutas.ts` y enlace en `frontend/components/Sidebar.tsx`.

Queda fuera:

- Reportes contables o facturación fiscal (CFDI).
- Exportación a formatos PDF o CSV (el requerimiento especifica Excel y previsualización UI).
- Edición de datos operativos desde la pantalla de reportes (es módulo de solo lectura y auditoría).

## Definición de los 5 Reportes

### 1. Contenedores en Patio (`CONTAINERS-IN-YARD`)
- **Propósito:** Snapshot en tiempo real de todos los contenedores actualmente dentro del patio.
- **Filtro de base de datos:** `Contenedor.estado.in_(['ingresado', 'ubicado', 'en_estadia', 'en_servicio_especial'])`.
- **Estructura de Columnas (9 columnas):**
  1. `Contenedor` (string, ej: `CSNU7862291`)
  2. `Cliente` (razón social del cliente)
  3. `Tipo` (capitalizado: `Lleno` / `Vacío`)
  4. `Tamaño` (formato: `CONTENEDOR ESTANDAR 20"` / `40"` / `45"`)
  5. `Estadía` (número entero de días desde ingreso hasta la fecha actual)
  6. `Fecha de Entrada` (formato `DD/MM/YYYY HH:MM:SS`)
  7. `Sellos` (texto / sellos registrados o vacío)
  8. `Patio` (nombre/código del patio)
  9. `Viaje` (folio o número de viaje de entrada, ej: `ENT012191-SEP26`)
- **Filtros aplicables:** Patio, Cliente, Tipo (Lleno/Vacío), Tamaño.

### 2. Movimientos de Entrada (`ENTRY-MOVEMENTS`)
- **Propósito:** Historial cronológico de todos los movimientos de ingreso al patio.
- **Filtro de base de datos:** `Movimiento.tipo == 'ingreso'`.
- **Estructura de Columnas (12 columnas):**
  1. `Folio` (número consecutivo o identificador)
  2. `Número de Viaje` (código de viaje, ej: `ENT005263-MAR26`)
  3. `Fecha Entrada` (formato `DD/MM/YYYY HH:MM:SS`)
  4. `Estado` (ej: `Completado`)
  5. `Operador` (nombre del usuario o chofer registrado)
  6. `Placas` (placas de la unidad)
  7. `Economico` (número económico del tracto)
  8. `Transportista` (razón social de la línea transportista)
  9. `Cliente` (razón social del cliente)
  10. `Patio` (nombre del patio)
  11. `Contenedor` (número de contenedor)
  12. `Condición` (`Lleno` / `Vacío`)
- **Filtros aplicables:** Rango de Fechas (inicio/fin), Patio, Cliente.

### 3. Movimientos de Salida (`DEPARTURE-MOVEMENTS`)
- **Propósito:** Historial cronológico de todos los despachos y salidas del patio.
- **Filtro de base de datos:** `Movimiento.tipo == 'salida'`.
- **Estructura de Columnas (13 columnas):**
  1. `Folio` (número consecutivo)
  2. `Número de Viaje` (código de viaje, ej: `SAL011327-AGO26`)
  3. `Fecha Entrada` (fecha en que ingresó el contenedor al patio)
  4. `Fecha Salida` (formato `DD/MM/YYYY HH:MM:SS` del movimiento de salida)
  5. `Estado` (ej: `Completado`)
  6. `Operador` (nombre del usuario o chofer)
  7. `Placas` (placas del transporte de retiro)
  8. `Económico` (número económico)
  9. `Transportista` (línea transportista que retira)
  10. `Cliente` (razón social del cliente)
  11. `Patio` (nombre del patio)
  12. `Contenedor` (número de contenedor)
  13. `Condición` (`Lleno` / `Vacío`)
- **Filtros aplicables:** Rango de Fechas (inicio/fin), Patio, Cliente.

### 4. Reporte de Posiciones (`POSITIONS`)
- **Propósito:** Mapa de coordenadas físicas exactas de los contenedores colocados en la matriz del patio.
- **Filtro de base de datos:** `Contenedor.ubicacion_id.isnot(None)`.
- **Estructura de Columnas (7 columnas):**
  1. `No. CONTENEDOR` (código del contenedor)
  2. `POSICION` (código compuesto, ej: `2-1-4-2-1` o `A01-T04-R02-N1`)
  3. `CARRIL` (número u orden de carril)
  4. `TRAMO` (número u orden de tramo)
  5. `TIRA` (número u orden de tira)
  6. `ALTURA` (nivel vertical: 1 a 5)
  7. `FECHA` (fecha de asignación o último movimiento a la posición actual)
- **Filtros aplicables:** Patio, Carril, Nivel/Altura.

### 5. Servicios Especiales (`SPECIAL-SERVICES`)
- **Propósito:** Registro de maniobras especiales, inspecciones, consolidaciones o servicios realizados.
- **Filtro de base de datos:** `Movimiento.tipo == 'servicio'`.
- **Estructura de Columnas (7 columnas):**
  1. `Servicio` (nombre o tipo de servicio especial, ej: `LAVADO`, `CONEXION REEFER`, `INSPECCION`)
  2. `Cliente` (razón social del cliente)
  3. `Patio` (nombre del patio)
  4. `Contenedor` (número de contenedor o `N/A`)
  5. `Fecha de Servicio` (formato `DD/MM/YYYY HH:MM:SS`)
  6. `Cantidad` (valor numérico entero)
  7. `Unidad` (unidad de medida o `SERVICIO` / `HORAS`)
- **Filtros aplicables:** Rango de Fechas (inicio/fin), Patio, Cliente, Tipo de Servicio.

## Especificación del Formato Excel (openpyxl)

El generador en backend implementará la estructura visual exacta extraída de las plantillas de referencia:

```
+---------------------------------------------------------------------------------------+
| Fila 1 (A1:X1 Merged): Título del Reporte (Arial 16pt Bold, Fill #1F4E79, Font #FFFFFF) |
+---------------------------------------------------------------------------------------+
| Fila 2 (A2:X2 Merged): Subtítulo | Generado: DD/MM/YYYY, HH:MM:SS | Total: N         |
|                        (Arial 10pt Italic, Font #595959, Sin Relleno)                 |
+---------------------------------------------------------------------------------------+
| Fila 3: Fila en blanco separadora (Altura 12pt)                                       |
+---------------------------------------------------------------------------------------+
| Fila 4: ENCABEZADOS DE COLUMNA (Arial 11pt Bold, Fill #1F4E79, Font #FFFFFF, Borde)   |
+---------------------------------------------------------------------------------------+
| Fila 5: Registro 1 (Arial 10pt Regular, Fill #FFFFFF, Borde #D9D9D9)                   |
| Fila 6: Registro 2 (Arial 10pt Regular, Fill #F9F9F9 (Zebra), Borde #D9D9D9)          |
| ...                                                                                   |
+---------------------------------------------------------------------------------------+
```

### Reglas de Estilo Excel:
1. **Tipografía:** `Arial` en todo el documento.
2. **Paleta de Colores:**
   - Azul Marino Institucional: `#1F4E79` (Hex ARGB: `FF1F4E79`).
   - Texto Blanco: `#FFFFFF`.
   - Texto Subtítulo: `#595959`.
   - Relleno Zebra Par: `#F9F9F9` (Hex ARGB: `FFF9F9F9`).
   - Relleno Zebra Impar: `#FFFFFF`.
   - Líneas de Borde: `#D9D9D9` (Thin).
3. **Alturas de Fila:**
   - Fila 1 (Título): 40pt.
   - Fila 2 (Subtítulo y Metadatos): 22pt.
   - Fila 3 (Separador): 12pt.
   - Fila 4 (Encabezados): 26pt.
   - Filas 5+ (Datos): 20pt.
4. **Alineación:**
   - Identificadores, fechas, estados y números: Centrados.
   - Nombres de clientes, patios y descripciones: Alineados a la izquierda.
   - Cantidades y pesos: Alineados a la derecha.
5. **Auto-ajuste de Ancho de Columnas:**
   - Cada columna se ajusta dinámicamente con base en la longitud máxima del contenido más un padding de seguridad de 4 caracteres.

## Arquitectura de Envíos Automáticos (APScheduler + SendGrid)

### Flujo de Ejecución del Scheduler:
1. Al iniciar FastAPI (`lifespan`), se inicializa `AsyncIOScheduler`.
2. Se leen todas las programaciones activas en la tabla `reportes_programados` y se registran como cron jobs en memoria.
3. Cuando vence un cron:
   - Se crea una sesión de base de datos asíncrona (`AsyncSession`).
   - Se ejecutan las consultas de `reportes_datos.py` según los filtros configurados.
   - Se genera el libro binario con `reportes_excel.py`.
   - Se adjunta el archivo `.xlsx` codificado en base64 en un correo transaccional vía SendGrid (`sendgrid.helpers.mail.Attachment`).
   - Se envía a la lista de destinatarios.
   - Se actualiza el registro en la BD: `ultimo_envio = now()`, `ultimo_estado = 'exitoso'` (o `'fallido'` con el trace de error en `ultimo_error`).
4. Al crear, editar o eliminar programaciones vía API, el scheduler añade, recalcula o elimina el job dinámicamente (`scheduler.add_job`, `scheduler.modify_job`, `scheduler.remove_job`).

### Modelo de Base de Datos: `ReporteProgramado` (`backend/app/models/reporte_programado.py`)

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `id` | `UUID` (PK) | Identificador único |
| `nombre` | `String(150)` | Nombre descriptivo del envío (ej: "Envío Diario Clientes") |
| `tipo_reporte` | `Enum(ReporteTipo)` | Uno de los 5 tipos de reportes |
| `patio_id` | `UUID` (FK nullable) | Patio opcional para filtrar |
| `cliente_id` | `UUID` (FK nullable) | Cliente opcional para filtrar |
| `frecuencia` | `Enum(diario, semanal, mensual)` | Periodicidad del envío |
| `hora` | `Integer` (0-23) | Hora de ejecución (ej. 8 para 08:00 AM) |
| `minuto` | `Integer` (0-59) | Minuto de ejecución (ej. 0) |
| `dia_semana` | `Integer` (nullable, 0-6) | 0=Lunes, 6=Domingo (para semanal) |
| `dia_mes` | `Integer` (nullable, 1-31) | Día del mes (para mensual) |
| `destinatarios` | `JSON / ARRAY(String)` | Lista de correos electrónicos válidos |
| `asunto` | `String(255)` | Asunto del correo electrónico |
| `mensaje` | `Text` (nullable) | Mensaje adicional en el cuerpo del correo |
| `activo` | `Boolean` (default True) | Si la tarea está habilitada |
| `ultimo_envio` | `DateTime` (nullable) | Fecha y hora de la última ejecución |
| `ultimo_estado` | `String(50)` (nullable) | `exitoso` o `fallido` |
| `ultimo_error` | `Text` (nullable) | Detalle del error si falló |
| `created_at` | `DateTime` | Fecha de creación |
| `updated_at` | `DateTime` | Fecha de última modificación |

## Arquitectura de Backend

### Nuevas Dependencias
- `openpyxl==3.1.5`
- `apscheduler==3.10.4`

### Nuevos Schemas Pydantic (`backend/app/schemas/reportes.py`)
- `ReporteTipo` (Enum): `containers-in-yard`, `entry-movements`, `departure-movements`, `positions`, `special-services`.
- `FrecuenciaReporte` (Enum): `diario`, `semanal`, `mensual`.
- `FiltrosReporte` (BaseModel): `fecha_inicio`, `fecha_fin`, `patio_id`, `cliente_id`, `busqueda`, `page`, `page_size`.
- `ReporteColumna` (BaseModel): `key`, `label`, `align`.
- `ReporteKpi` (BaseModel): `label`, `value`, `subtext`, `tone`.
- `ReportePreviewOut` (BaseModel): `tipo`, `titulo`, `subtitulo`, `total_registros`, `columnas`, `filas`, `kpis`, `page`, `page_size`, `total_paginas`.
- `ReporteProgramadoCreate` (BaseModel): `nombre`, `tipo_reporte`, `patio_id`, `cliente_id`, `frecuencia`, `hora`, `minuto`, `dia_semana`, `dia_mes`, `destinatarios`, `asunto`, `mensaje`, `activo`.
- `ReporteProgramadoUpdate` (BaseModel): campos opcionales para edición.
- `ReporteProgramadoOut` (BaseModel): schema completo con `id`, `ultimo_envio`, `ultimo_estado`, `ultimo_error`, timestamps.

### Actualización en `backend/app/core/email.py`
Función `enviar_correo_con_adjunto(destinatarios: list[str], asunto: str, contenido_html: str, adjunto_bytes: bytes, adjunto_nombre: str)` que adjunta el archivo Excel en base64 usando las clases `Attachment`, `FileContent`, `FileName`, `FileType`, `Disposition` de SendGrid.

### Nuevo Servicio Scheduler (`backend/app/services/reportes_scheduler.py`)
- Gestor singleton de `AsyncIOScheduler`.
- `iniciar_scheduler(app)` / `apagar_scheduler()`.
- `sincronizar_tareas_desde_db(db)`: Registra o actualiza los jobs cron.
- `ejecutar_tarea_envio(reporte_programado_id)`: Genera datos, crea Excel, envía correo y actualiza estado en BD.

### Nuevas Rutas de API (`backend/app/api/routes/reportes.py`)
Prefijo: `/api/reportes`
Seguridad: `require_roles(RolUsuario.OPERADOR, RolUsuario.SUPERVISOR, RolUsuario.ADMIN)`.

| Método | Ruta | Descripción | Respuesta |
| --- | --- | --- | --- |
| GET | `/api/reportes/{tipo}/preview` | Datos paginados y KPIs para previsualización UI | `ReportePreviewOut` |
| GET | `/api/reportes/{tipo}/exportar` | Generación y streaming del archivo Excel .xlsx | `StreamingResponse` (.xlsx) |
| GET | `/api/reportes/programados` | Listar todas las tareas programadas | `list[ReporteProgramadoOut]` |
| POST | `/api/reportes/programados` | Crear una nueva tarea de envío automático | `ReporteProgramadoOut` |
| GET | `/api/reportes/programados/{id}` | Obtener detalle de una tarea programada | `ReporteProgramadoOut` |
| PATCH | `/api/reportes/programados/{id}` | Modificar configuración, horario o estado activo | `ReporteProgramadoOut` |
| DELETE | `/api/reportes/programados/{id}` | Eliminar una tarea programada | `204 No Content` |
| POST | `/api/reportes/programados/{id}/ejecutar` | Disparar envío de prueba inmediato | `{"detail": "Reporte enviado exitosamente"}` |

## Arquitectura de Frontend

### Cliente API (`frontend/lib/api.ts`)
- `ReporteTipo`, `FrecuenciaReporte`, `ReporteProgramado`, `ReporteProgramadoPayload`.
- `obtenerPreviewReporte(token, tipo, filtros)`
- `descargarReporteExcel(token, tipo, filtros, nombreArchivo)`
- `listarReportesProgramados(token)`
- `crearReporteProgramado(token, payload)`
- `actualizarReporteProgramado(token, id, payload)`
- `eliminarReporteProgramado(token, id)`
- `ejecutarReporteProgramadoManual(token, id)`

### Componentes de UI (`frontend/components/reportes/`)
1. `CatalogoReportes.tsx`: Lista lateral con buscador de reportes y tarjetas temáticas con iconos y badges.
2. `FiltrosReporteBar.tsx`: Barra superior con selectores de fechas, patio, cliente, búsqueda y botones "Descargar Excel" y "Programar Envío".
3. `ResumenKpisReporte.tsx`: Tira de 3 a 4 tarjetas de métricas resumidas.
4. `TablaPreviewReporte.tsx`: Envoltorio de `DataTable` con paginación y estados vacíos.
5. `ModalProgramarReporte.tsx`: Diálogo modal para configurar frecuencia (diario/semanal/mensual), hora, destinatarios y filtros del reporte automático.
6. `PanelReportesProgramados.tsx`: Vista/cajón con el listado de programaciones activas, histórico de últimos envíos y botones para probar, pausar o eliminar.

### Pantalla Principal (`frontend/app/reportes/page.tsx`)
- Master-detail view con cambio fluido entre modo "Previsualización" y modal de "Automatizaciones y Envíos Programados".
