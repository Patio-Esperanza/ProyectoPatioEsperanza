# Reporte de estancia por día

Fecha: 2026-11-17
Estado: propuesto; se integra al módulo de `2026-09-30-modulo-reportes-design.md`
Versión editable: https://claude.ai/artifact/K3ag2AonwqY5ihwBVDsb1w

## Relación con el módulo de reportes (2026-09-30 y 2026-10-22)

Este spec se escribió sin conocer el módulo de reportes existente. Ese módulo ya tiene
`/reportes`, cinco reportes, Excel con formato institucional (`#1F4E79`, Arial), envíos
programados con APScheduler y acceso del cliente filtrado por `cliente_id`. Para no
duplicarlo:

- **No se crean endpoints propios.** Los reportes nuevos se agregan como valores de
  `ReporteTipo` y usan `GET /api/reportes/{tipo}/preview` y `/exportar`.
- **Sin CSV.** El módulo exporta solo Excel y el cliente imprime a PDF; se respeta.
- **Excel** con el mismo formato institucional del módulo.
- **Envíos programados**: los reportes nuevos se pueden programar con
  `reportes_programados` sin trabajo extra.
- **La columna `Estadía` de `Contenedores en Patio` (`containers-in-yard`) debe leer
  `v_estancias`**, para que el número de días sea el mismo en todos los reportes. Hoy cuenta
  "días desde ingreso hasta la fecha actual"; con la regla del día 1 da un día más.
- **Servicios**: la columna de servicios del reporte de estancia lee `servicios_contenedor`
  (ver `2026-11-17-servicios-especiales-design.md`).

## Resumen

La estancia de cada contenedor se calcula con una sola regla, guardada en una vista de
base de datos, y cada noche un corte guarda la foto del patio. Con eso se agregan tres
reportes al módulo existente: inventario a una fecha, estancia por cliente y resumen
diario. Corresponde a la Fase 3 de `2026-11-17-mejoras-operativas-patio-design.md` y
depende de la Fase 1, que registra la hora real de ingreso y salida.

| Usuario | Para qué lo usa |
| --- | --- |
| Admin del patio | Saber qué hay en patio, cobrar estancias, ver la ocupación por día |
| Operación | Detectar contenedores con estancia prolongada |
| Cliente | Ver los días de cada uno de sus contenedores y descargar su reporte |

`en_estadia` deja de usarse como estado. La estancia es un cálculo: un contenedor
`ubicado` ya está en estancia.

## Reglas de cálculo

Se cuentan días calendario en hora de Ciudad de México, desde el día del ingreso hasta el
día de la salida. El día de ingreso cuenta como día 1 y los días libres se pactan por
cliente (decidido el 17 nov 2026).

- **Inicio**: hora del movimiento de ingreso (el que deja el contenedor en `ingresado`), no
  la hora de la solicitud.
- **Fin**: hora del movimiento de salida (`despachado`). Si sigue en patio, se usa el
  momento de la consulta, o el cierre del día en el corte diario.
- **Zona horaria**: las fechas se guardan en UTC y se convierten a `patios.zona_horaria`
  (por defecto `America/Mexico_City`) **antes** de tomar el día. Un ingreso a las 22:40
  locales ya es el día siguiente en UTC.
- **Días de estancia**: `fecha_fin − fecha_inicio + 1`. Un contenedor que entra y sale el
  mismo día cuenta 1 día.
- **Días libres**: `clientes.dias_libres`; 0 si el cliente no tiene días pactados.
- **Días cobrables**: el mayor entre 0 y (días de estancia menos días libres).

### Ejemplo resuelto (5 días libres)

| Caso | Ingreso | Salida | Días de estancia | Días cobrables |
| --- | --- | --- | --- | --- |
| Estancia normal | 3 nov 22:40 | 10 nov 08:15 | 8 | 3 |
| Sale el mismo día | 5 nov 07:00 | 5 nov 18:00 | 1 | 0 |
| Sigue en patio, consulta del 17 nov | 14 nov 10:00 | — | 4 | 0 |

## Datos y corte diario

La regla vive en un solo lugar, la vista `v_estancias`, y todo lo demás la lee: la API, el
corte y los reportes. Así el número de días nunca cambia según la pantalla.

### Columnas nuevas

| Tabla | Columna | Tipo | Uso |
| --- | --- | --- | --- |
| `patios` | `zona_horaria` | texto, por defecto `America/Mexico_City` | Conversión a día local |
| `patios` | `umbral_estancia_dias` | entero, nulo | Alerta de estancia prolongada |
| `clientes` | `dias_libres` | entero, por defecto 0 | Días libres pactados con el cliente |
| `contenedores` | `ingresado_en` | timestamptz | Copia de la hora del movimiento de ingreso, con índice |

`fecha_salida` ya la agrega la Fase 1B. `ingresado_en` se llena en la misma transacción
del ingreso y se rellena para los contenedores existentes desde `movimientos`.

### Vista `v_estancias`

Una fila por contenedor que ya ingresó: contenedor, patio, cliente, `ingresado_en`,
`fecha_salida`, `dias_estancia`, `dias_libres_aplicados`, `dias_cobrables`. La vista hereda
el RLS de `contenedores`.

### Tabla `inventario_diario`

Columnas: fecha, patio_id, contenedor_id, cliente_id, ubicacion_id, estado, dias_estancia.
Llave única (fecha, patio_id, contenedor_id) y RLS por patio.

### Job nocturno

- Corre a las 00:10 hora local y genera el corte **del día anterior**. Puede registrarse en
  el mismo `AsyncIOScheduler` del módulo de reportes.
- Reconstruye qué había en patio a las 23:59:59 a partir de `movimientos`, no del estado
  actual. Por eso se puede repetir para cualquier fecha.
- Es idempotente: borra e inserta el corte de esa fecha y ese patio en una transacción.
- Comando `python -m app.jobs.corte_diario --desde 2026-09-14 --hasta ayer` para llenar el
  historial y para corregir días cuando se ajusta un movimiento.
- Si falla, queda registrado en auditoría y el tablero del admin muestra "Corte pendiente"
  para esa fecha.

## Reportes nuevos en el módulo

| `ReporteTipo` | Título | Fuente | Columnas | Roles |
| --- | --- | --- | --- | --- |
| `inventory-at-date` | Inventario a una fecha | `inventario_diario` (hoy: `v_estancias`) | Contenedor, cliente, ubicación, estado, días de estancia | Staff |
| `stay-by-client` | Estancia por cliente | `v_estancias` | Contenedor, ingreso, salida, días, días libres, días cobrables, servicios realizados | Staff, cliente (suyos) |
| `daily-summary` | Resumen diario | `inventario_diario` y `movimientos` | Fecha, entradas, salidas, saldo al cierre, ocupación % | Staff |

Filtros: los del módulo (rango de fechas, patio, cliente, búsqueda) más `fecha` para el
inventario. Un rango mayor a 366 días responde 422. KPIs sugeridos para
`stay-by-client`: contenedores, días totales, días cobrables, promedio de estancia.

### Pantallas

- **`/reportes`**: los tres reportes aparecen en el catálogo lateral existente.
- **Detalle del contenedor**: días en patio, días libres restantes y días cobrables,
  visibles para internos y para el cliente.
- **Portal del cliente**: en Mis contenedores, cada tarjeta muestra los días y una etiqueta
  "Quedan 2 días libres" cuando aplica.

### Alertas

- Si el patio tiene `umbral_estancia_dias`, el tablero del admin lista los contenedores que
  lo rebasan, ordenados por días.
- Opcional: correo al cliente cuando a un contenedor le queda un día libre. Lo envía el
  mismo job nocturno.

## Pruebas (TDD)

- Los tres casos del ejemplo resuelto dan exactamente esos días.
- Ingreso a las 23:30 locales: cuenta para ese día, no para el siguiente.
- Cliente sin días libres pactados: todos los días son cobrables.
- Días libres mayores que la estancia: 0 cobrables, nunca negativos.
- La columna `Estadía` de `containers-in-yard` coincide con `v_estancias`.
- Correr dos veces el corte de la misma fecha deja el mismo resultado.
- Corte de una fecha pasada: coincide con lo que dicen los movimientos de esa fecha,
  aunque el contenedor ya haya salido.
- Un cliente pide `stay-by-client` de otro cliente: recibe solo lo suyo.
- El Excel abre con el formato institucional y las fechas como fechas, no como texto.

## Fuera de alcance

Facturación y tarifas, cobro por fracción de 24 horas y gráficas históricas en el tablero.

## Decisiones tomadas (17 nov 2026)

- El día de ingreso cuenta como día 1.
- Los días libres se pactan por cliente.

## Preguntas abiertas

- [ ] ¿Se cobra por día calendario o por periodos de 24 horas desde el ingreso?
- [ ] ¿Cuántos días se consideran estancia prolongada en cada patio?
