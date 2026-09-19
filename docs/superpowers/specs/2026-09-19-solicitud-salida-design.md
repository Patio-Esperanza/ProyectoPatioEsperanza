# Solicitud de salida + relación cliente↔contenedores + cola de planeación de grúa — Design

**Fecha:** 2026-09-19

## Contexto

Hasta ahora el sistema solo cubre el flujo de entrada de contenedores (Portal Cliente Spec 1 y Spec 2: alta de cliente, solicitud de entrada con PIN de confirmación). No existe ningún flujo de salida: `EstadoContenedor` define los estados `SOLICITUD_SALIDA`, `QR_SALIDA_EMITIDO`, `EN_PORTERIA_SALIDA`, `DESPACHADO` desde el plan original (`docs/superpowers/plans/2026-09-14-backend-foundation.md:1638`), pero ningún endpoint los usa todavía.

Tampoco existe forma de listar contenedores: `GET /api/contenedores/{id}` (uno por uno) es el único endpoint de lectura. No hay "mis contenedores" para el cliente ni una cola de trabajo para el staff.

El cliente necesita ver cuáles de sus contenedores están en el patio y pedir la salida de uno específico. El staff necesita ver esas solicitudes con anticipación para planear los movimientos de la grúa.

## Decisiones confirmadas con el usuario

- El cliente inicia la solicitud de salida, con el mismo patrón que la solicitud de entrada (`POST /api/contenedores/solicitar`, Spec 1): el cliente ve sus contenedores y pide la salida de uno.
- `fecha_estimada_retiro` (capturada en la solicitud de entrada, columna real `fecha_estimada_salida`) es solo una referencia para decidir el acomodo inicial — no ata ni predice la salida real. La salida real se dispara cuando el cliente la solicita, en cualquier momento. Se usa un campo nuevo y distinto para la fecha real deseada de salida.
- El staff no necesita cálculo de capacidad ni calendario: basta una cola/lista de solicitudes de salida pendientes, ordenada por fecha deseada, para planear manualmente los movimientos de grúa.
- El tiempo mínimo de anticipación para poder solicitar salida es **configurable por patio** (algunos patios pueden reubicar y sacar un contenedor más rápido que otros).

## Elegibilidad para solicitar salida

`EstadoContenedor` tiene 12 valores, pero hoy solo tres son alcanzables vía API: `SOLICITUD_INGRESO` (al crear), `EN_PORTERIA` (al verificar PIN, Spec 2), `UBICADO` (al registrar un `POST /movimientos`, que hoy no valida el estado previo — ver `backend/app/api/routes/movimientos.py`). `EN_ESTADIA` y `EN_SERVICIO_ESPECIAL` existen en el enum pero ningún endpoint los asigna — son estados futuros, fuera de esta spec.

Por lo tanto: solo un contenedor con `estado == UBICADO` puede tener una solicitud de salida. Es el único estado que representa de forma confiable "contenedor colocado en el patio, disponible".

## Arquitectura

### Backend

**Migración Alembic nueva** — agrega:
- `patios.anticipacion_minima_horas: int` (`NOT NULL DEFAULT 24`).
- `contenedores.fecha_deseada_salida: datetime | None` (`TIMESTAMPTZ`) — fecha real solicitada por el cliente para la salida.
- `contenedores.salida_solicitada_en: datetime | None` (`TIMESTAMPTZ`) — momento en que se registró la solicitud (auditoría/orden).

`backend/app/models/ubicacion.py` (`Patio`) y `backend/app/models/contenedor.py` (`Contenedor`): agregar los campos anteriores.

**`PATCH /api/patios/{id}`** (nuevo, admin-only, `require_roles(ADMIN)`) — primer endpoint de edición del proyecto (hoy `patios.py` solo tiene `POST` y `GET`, ningún otro recurso tiene edición tampoco). Alcance acotado: solo actualiza `anticipacion_minima_horas` (body `{ anticipacion_minima_horas: int }`). No se generaliza a editar `nombre`/`codigo`/`activo` — no se pidió y evita abrir un endpoint de edición más amplio sin necesidad concreta.

**`GET /api/contenedores`** (nuevo — no existe listado hoy, solo `GET /{id}`):
- Rol `CLIENTE`: fuerza `cliente_id = user.cliente_id` sin importar query params — el cliente nunca puede pedir contenedores de otra empresa.
- Roles `OPERADOR`/`SUPERVISOR`/`ADMIN`: acepta filtros opcionales por query string, `estado` y `patio_id` (y `cliente_id` para admin). Sin filtros, devuelve todos (respetando RLS por patio vía `get_scoped_db`, igual que `GET /{id}`).
- Orden: por `fecha_deseada_salida` ascendente cuando el filtro incluye `estado=solicitud_salida` (para que la cola de planeación salga ya ordenada); si no, por `created_at` descendente (más reciente primero), igual que cualquier listado del proyecto.
- `ContenedorOut` gana el campo `anticipacion_minima_horas: int` (del `Patio` relacionado, vía join) y `fecha_deseada_salida: datetime | None` — el cliente necesita ver el mínimo de anticipación de su patio antes de elegir fecha.

**`POST /api/contenedores/{id}/solicitar-salida`** (`require_roles(CLIENTE)`). Body `{ fecha_deseada_salida: datetime }`.
1. Busca el contenedor por id. No existe → `404`.
2. `contenedor.cliente_id != user.cliente_id` → `403` ("No autorizado para solicitar la salida de este contenedor").
3. `contenedor.estado != UBICADO` → `409` ("Este contenedor no está disponible para solicitar salida").
4. Carga el `Patio` del contenedor para leer `anticipacion_minima_horas`. Si `fecha_deseada_salida < now() + anticipacion_minima_horas` → `422` ("La fecha de salida debe ser al menos {N} horas después de ahora para este patio").
5. Si todo pasa: `estado = SOLICITUD_SALIDA`, `fecha_deseada_salida = payload.fecha_deseada_salida`, `salida_solicitada_en = now()`. Auditoría (`accion="solicitar_salida"`, mismo patrón que los demás handlers). `commit()`, devuelve `ContenedorOut`.

### Frontend

- `frontend/app/mis-contenedores/page.tsx` (nuevo, `AuthGuard`, visible solo `user.rol === "cliente"`): tabla de los contenedores del cliente (`GET /contenedores`, scoping automático por rol). Cada fila en `UBICADO` tiene un botón "Solicitar salida" que abre un formulario inline con la anticipación mínima visible (`anticipacion_minima_horas` del contenedor) y un input de fecha/hora.
- `frontend/app/salidas/page.tsx` (nuevo, `AuthGuard`, visible solo `operador`/`supervisor`/`admin`): cola de solicitudes de salida (`GET /contenedores?estado=solicitud_salida`), tabla ordenada por `fecha_deseada_salida`, con selector de patio para filtrar (reutiliza `PatioSelect` ya existente).
- `frontend/lib/api.ts`: `listarContenedores(token, filtros?: { estado?, patio_id?, cliente_id? }): Promise<Contenedor[]>`, `solicitarSalida(token, id, fecha_deseada_salida): Promise<Contenedor>`. `Contenedor` gana `anticipacion_minima_horas?: number` y `fecha_deseada_salida?: string | null`.
- `NavBar`: nuevo link "Mis contenedores" para `cliente`, nuevo link "Salidas" para `operador`/`supervisor`/`admin`.

## Validación y manejo de errores

- `solicitar-salida` con contenedor de otra empresa → `403`.
- `solicitar-salida` con estado distinto de `UBICADO` → `409`.
- `solicitar-salida` con fecha menor al mínimo de anticipación del patio → `422`, mensaje incluye el mínimo en horas.
- `PATCH /patios/{id}` con rol no admin → `403`; patio inexistente → `404`; `anticipacion_minima_horas` negativo o cero → `422` (validación Pydantic, `gt=0`).
- `GET /contenedores` como cliente ignora cualquier `cliente_id`/`patio_id` que se intente pasar por query string — siempre fuerza el propio `cliente_id`.

## Testing

**Backend:**
- `test_patios_api.py` (ampliado): admin puede `PATCH /patios/{id}` `anticipacion_minima_horas`; no-admin da `403`; valor `<=0` da `422`; patio inexistente da `404`.
- `test_contenedores_api.py` (ampliado):
  - `GET /contenedores` como cliente solo devuelve los suyos, ignora filtros de otro `cliente_id`.
  - `GET /contenedores?estado=solicitud_salida` como staff devuelve ordenado por `fecha_deseada_salida` ascendente.
  - `POST /{id}/solicitar-salida`: caso feliz cambia estado a `solicitud_salida` y guarda fechas; dueño distinto da `403`; estado distinto de `UBICADO` da `409`; fecha menor al mínimo del patio da `422`; contenedor inexistente da `404`.

**Frontend:** tests para `/mis-contenedores` (lista, botón condicional por estado, envío de solicitud), `/salidas` (lista ordenada, filtro por patio), y las funciones nuevas de `lib/api.ts`.

## Fuera de alcance

- Cálculo de capacidad de grúa por día/turno.
- Transición automática de `SOLICITUD_SALIDA` a `DESPACHADO` (requiere QR de salida, spec aparte — simétrico a la Spec 3 de entrada, aún no diseñada).
- Estados `EN_ESTADIA` / `EN_SERVICIO_ESPECIAL` (ningún endpoint los asigna hoy, no se agregan en esta spec).
- Reasignación de patio o ubicación al solicitar salida.
- Edición de `nombre`/`codigo`/`activo` de `Patio` (el `PATCH` nuevo solo cubre `anticipacion_minima_horas`).
- Cancelar o modificar una solicitud de salida ya creada.

## Self-review

- Sin placeholders/TBD.
- Verificado en código real (no asumido) que `EN_ESTADIA`/`EN_SERVICIO_ESPECIAL` no los asigna ningún endpoint — justifica que la elegibilidad de salida sea solo `UBICADO`.
- Verificado que no existe ningún endpoint `PATCH`/`PUT` en el proyecto — se documenta explícitamente que `PATCH /patios/{id}` es el primero, y se acota su alcance a un solo campo para no abrir edición general sin necesidad.
- Verificado que `GET /api/contenedores` (listado) no existe — se documenta como endpoint nuevo, no una ampliación de uno existente.
- `fecha_deseada_salida` y `salida_solicitada_en` son columnas nuevas y distintas de `fecha_estimada_salida` (ya usada por Spec 1) — evita colisión semántica confirmada explícitamente por el usuario.
- Alcance acotado a: listado con scoping por rol, solicitud de salida con validación de anticipación por patio, cola de planeación. Sin QR de salida, sin cálculo de capacidad.
