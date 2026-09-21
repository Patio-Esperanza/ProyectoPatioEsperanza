# Contexto del proyecto — Patio Esperanza

Última actualización: 2026-09-20. Rama `master`, último commit `8db0890`.

## Qué es

Sistema de gestión de patio de contenedores. Un backend FastAPI expone la API y un
dashboard Next.js consume esa API. El sistema cubre el ciclo de vida del contenedor:
solicitud de entrada por parte del cliente, confirmación en portería con PIN, ubicación
dentro del patio, movimientos internos y solicitud de salida con cola de planeación de grúa.

## Stack verificado

**Backend** (`backend/`)
- FastAPI + SQLAlchemy 2.0 async + asyncpg
- PostgreSQL 16, migraciones Alembic (`0001` a `0010`)
- Auth JWT (PyJWT + passlib/bcrypt). El rol y los patios asignados viajan dentro del JWT
  (`sub`, `rol`, `patios`, `cliente_id` opcional). No existe endpoint `/me`.
- Row-Level Security por `patio_id` a nivel de base de datos
- Envío de correo vía SendGrid (`app/core/email.py`)
- Tests: pytest + pytest-asyncio + httpx

**Frontend** (`frontend/`)
- Next.js 14.2.35 App Router + TypeScript 5.9.3, React 18.3.1, componentes cliente
- Sin librería de UI externa. CSS Modules + variables CSS de marca.
- Sesión JWT en `localStorage` bajo la llave `patio_esperanza_token`
- Tests: Vitest 5 + React Testing Library

**Infra**
- Despliegue en DigitalOcean App Platform (`app.yaml`): servicios `api`, `web`,
  `background-jobs` y base de datos administrada
- Desarrollo local con Docker Compose (Postgres en el puerto 5433)

## Estructura

```
backend/app/api/routes/   Endpoints HTTP
backend/app/models/       Modelos SQLAlchemy y enums
backend/app/core/         Seguridad, auditoría, email, validación ISO 6346
backend/app/alembic/      Migraciones 0001-0010
backend/tests/            18 archivos de test
frontend/app/             Rutas del App Router, cada una con su test colocado al lado
frontend/components/      AuthGuard, NavBar, PatioSelect
frontend/lib/             api.ts, auth-context.tsx, jwt.ts, use-patios-disponibles.ts
docs/superpowers/specs/   Documentos de diseño, uno por feature
docs/superpowers/plans/   Planes de implementación paso a paso
docker/initdb/            Scripts de inicialización de la base de datos
```

## Estado de las pruebas

Ambas suites corren en verde al momento de escribir este documento.

- Backend: `82 passed` (`cd backend && pytest`)
- Frontend: `100 passed` en 24 archivos (`cd frontend && npx vitest run`)
- `cd frontend && npx tsc --noEmit` sale limpio.

`npm run lint` no funciona: el repositorio nunca tuvo `.eslintrc` y `next lint` pide
crearlo de forma interactiva. Queda pendiente configurarlo.

## Endpoints implementados

| Método | Ruta | Notas |
|---|---|---|
| POST | `/api/auth/login` | Devuelve JWT |
| GET | `/api/health`, `/api/health/db` | Healthchecks |
| GET, POST | `/api/patios` | Crear requiere admin |
| PATCH | `/api/patios/{id}` | Solo `anticipacion_minima_horas`, admin |
| GET, POST | `/api/usuarios` | Admin |
| GET, POST | `/api/clientes` | Admin |
| POST | `/api/clientes/registro` | Registro público de personal de cliente |
| POST | `/api/clientes/verificar` | Verificación por código enviado a correo |
| GET | `/api/contenedores` | Listado con scoping por rol y filtros |
| POST | `/api/contenedores` | Alta interna, validación ISO 6346 |
| POST | `/api/contenedores/solicitar` | Solicitud de entrada del cliente, genera PIN |
| POST | `/api/contenedores/verificar-pin` | Portería |
| GET | `/api/contenedores/{id}/pin` | Ver PIN, permiso restringido |
| POST | `/api/contenedores/{id}/solicitar-salida` | Valida anticipación mínima del patio |
| GET | `/api/contenedores/{id}` | Detalle |
| POST | `/api/movimientos` | Ingreso, reubicación, servicio, salida, con locking de slot |
| POST | `/api/ubicaciones/sugerir` | Algoritmo de scoring |

## Páginas del frontend

`/login`, `/patios`, `/contenedores`, `/contenedores/[id]`, `/movimientos`,
`/ubicaciones/sugerir`, `/usuarios`, `/clientes`, `/porteria`, `/salidas`,
`/solicitar`, `/mis-contenedores`, `/registro`, `/registro/verificar`.

## Máquina de estados del contenedor

`EstadoContenedor` declara doce estados:
`solicitud_ingreso`, `qr_ingreso_emitido`, `en_porteria`, `ingresado`, `ubicado`,
`en_estadia`, `en_servicio_especial`, `solicitud_salida`, `qr_salida_emitido`,
`en_porteria_salida`, `despachado`, `rechazado`.

Hoy ningún endpoint asigna `qr_ingreso_emitido`, `qr_salida_emitido`,
`en_porteria_salida`, `en_estadia` ni `en_servicio_especial`. Son estados declarados pero
todavía sin flujo que los produzca.

## Alcance original del proyecto

El documento de alcance completo (referido en los planes como "spec artifact sección 10" y
"roadmap v1") no está versionado en este repositorio. La lista de subsistemas que lo componen
se reconstruye a partir de los encabezados "Fuera de alcance" de los dos planes fundacionales:

- `docs/superpowers/plans/2026-09-14-backend-foundation.md:11` — QR firmado y portería,
  portal cliente, PWA offline, mapa SVG, SSO e identidades federadas, API de socios
  (Kasu/Loginco), deploy a DigitalOcean.
- `docs/superpowers/plans/2026-09-17-frontend-dashboard.md:11` y `:3116` — portal cliente
  (solicitudes, ver QR), flujo QR y portería, PWA offline, mapa SVG con drag and drop,
  CRUD de usuarios y geocercas, API de socios. Nombra las tablas que faltarían:
  `solicitudes`, `qr_tokens`, `escaneos_qr`, `sync_operaciones`.

Ese es el universo contra el cual se mide el avance en las dos listas siguientes.

## Implementado, según el historial de git

68 commits, del scaffold inicial `af27be3` al fix `ecbcce2`. Agrupados por subsistema:

### Fundación del backend (14 commits, `af27be3` a `12cee83`)

| Commit | Entrega |
|---|---|
| `af27be3` | Scaffold FastAPI con health check |
| `a6e1867` | Engine async, Alembic, health check contra la base de datos real |
| `b907c46` | Jerarquía patio, carril, tramo, tira, nivel con constraints |
| `748f41a` | Modelos `Cliente`, `Usuario`, `UsuarioPatio` con RBAC base |
| `e5632bc` | Auditoría append-only, rol `patio_app` sin UPDATE ni DELETE |
| `8e14a97` | `Contenedor` y `Movimiento`, máquina de estados, checksum ISO 6346 |
| `ec802b0` | Hashing bcrypt y JWT HS256 |
| `a96572b` | `get_current_user`, `require_roles`, `POST /auth/login` |
| `fa871ff` | CRUD de patios con auditoría, admin |
| `1aca9c7` | CRUD de contenedores con validación ISO 6346 y auditoría |
| `dd046ec` | `POST /movimientos` con locking de slot y transición de estado |
| `3f3b4b8` | Algoritmo de sugerencia de ubicación por scoring |
| `12cee83` | RLS por `patio_id` en contenedores, movimientos y auditoría |

### Dashboard interno (8 commits, `4c52efd` a `a1d2f21`)

Scaffold Next.js 14 con Vitest, cliente HTTP tipado, `AuthContext` con sesión en
`localStorage`, `AuthGuard`, `NavBar` con logo, y las páginas de patios, contenedores
(alta y detalle), movimientos y sugerencia de ubicación.

### Gestión de usuarios internos (9 commits, `8ed7a59` a `bfdd2e5`)

Endpoint de alta y listado de usuarios internos, cliente HTTP, hook
`usePatiosDisponibles`, componente `PatioSelect`, auto-relleno de patio en dos formularios,
página `/usuarios` admin-only. Cubre el punto "CRUD de usuarios (admin)" del roadmap v1,
salvo editar y desactivar.

### Portal cliente Spec 1, fundación (11 commits, `197580a` a `2cdb245`)

Columnas de verificación de correo y configuración SendGrid, wrapper de envío de correo,
`cliente_id` opcional en el JWT de forma retrocompatible, CRUD admin de empresas cliente,
registro y verificación por código del personal del cliente, solicitud de entrada de
contenedor, y las páginas `/registro`, `/registro/verificar`, `/solicitar` y `/clientes`.

### Portal cliente Spec 2, PIN (8 commits, `825e682` a `ed8c20d`)

Columnas de PIN en `contenedores`, generación y envío del PIN en la solicitud, `GET
/contenedores/{id}/pin`, `POST /contenedores/verificar-pin`, botón "Ver PIN" en el detalle
y página `/porteria`. Es un sustituto del QR de entrada, no el QR mismo.

### Solicitud de salida (11 commits, `4d00827` a `a62a2fa`)

Columnas `anticipacion_minima_horas` en `patios` y `fecha_deseada_salida` y
`salida_solicitada_en` en `contenedores`, `PATCH /api/patios/{id}`, `GET /api/contenedores`
con scoping por rol, `POST /api/contenedores/{id}/solicitar-salida` con validación de
anticipación, y las páginas `/mis-contenedores` y `/salidas`.

### Correcciones (2 commits)

`bfdd2e5` agrega `cors_origins_list` que faltaba en `config.py`. `ecbcce2` cierra la fuga
de contexto RLS entre requests por reuso de conexión del pool, con la migración `0010`.

### Tablas existentes hoy

`patios`, `carriles`, `tramos`, `tiras`, `ubicaciones`, `contenedores`, `movimientos`,
`clientes`, `usuarios`, `usuario_patio`, `auditoria`.

## Falta por implementar, contra el alcance original

### Subsistemas completos que no existen

| Subsistema | Estado | Tablas que faltarían |
|---|---|---|
| QR firmado de entrada y salida, portería | Sin spec. El PIN cubre solo la entrada. | `qr_tokens`, `escaneos_qr` |
| PWA offline para operación en patio | Sin spec ni diseño | `sync_operaciones` |
| Mapa SVG interactivo con drag and drop | Sin spec ni diseño | ninguna nueva |
| SSO e identidades federadas | `password_hash` ya es nullable para dejar espacio | `identidades_federadas` |
| API de socios (Kasu, Loginco) | Sin spec. `socio_api` existe como `TipoCliente`. | por definir |
| CRUD de geocercas | Sin spec ni modelo | por definir |
| Deploy a DigitalOcean | `app.yaml` existe. No hay evidencia en git de un deploy ejecutado. | ninguna |

### Estados declarados sin flujo que los produzca

`qr_ingreso_emitido`, `qr_salida_emitido`, `en_porteria_salida` dependen del flujo de QR.
`en_estadia` y `en_servicio_especial` no los asigna ningún endpoint y ninguna spec los cubre.
La transición de `solicitud_salida` a `despachado` sigue sin implementarse.

### Huecos dentro de lo ya entregado

- Editar y desactivar usuarios. `/usuarios` solo crea y lista.
- Editar `nombre`, `codigo` y `activo` de un patio. El `PATCH` solo toca la anticipación.
- Cancelar o modificar una solicitud de salida ya creada.
- Gate en `POST /movimientos` que impida ubicar un contenedor sin PIN verificado.
- Límite de reintentos o bloqueo por PIN incorrecto repetido.
- Constraint de unicidad sobre `numero_contenedor` en contenedores activos.
- Rate limiting en `registro` y `verificar`.
- Reenvío explícito del código de verificación y del PIN.
- Rutina inteligente de asignación de patio por lleno o vacío.
- Cálculo de capacidad de grúa por día o turno.
- Selector de contenedor y de ubicación en los formularios. Hoy `contenedor_id` y
  `ubicacion_destino_id` se escriben a mano como UUID.

## Trabajo entregado, por spec

1. **Fundación backend** (`2026-09-14`): auth, patios, jerarquía de ubicación
   (patio, carril, tramo, tira, ubicación), contenedores con validación ISO 6346,
   movimientos con locking, auditoría append-only, RLS por `patio_id`.
2. **Dashboard interno** (`2026-09-17`): login, guard de sesión, patios, contenedores,
   movimientos, sugerencia de ubicación.
3. **Gestión de usuarios** (`2026-09-18`): CRUD admin de usuarios internos y auto-relleno
   de patio en los formularios.
4. **Portal cliente Spec 1** (`2026-09-18`): alta de clientes empresa, registro y
   verificación por correo del personal del cliente, solicitud de entrada.
5. **Portal cliente Spec 2 — PIN** (`2026-09-19`): PIN de 4 dígitos generado en la
   solicitud, enviado por correo, consultable por admin y verificable en portería.
6. **Solicitud de salida** (`2026-09-19`): relación cliente-contenedores, página
   "Mis contenedores", validación de anticipación mínima por patio y cola de planeación
   de grúa en la página "Salidas".
7. **Fix de fuga RLS** (`2026-09-20`): los GUC `app.rol` y `app.patios_asignados` se
   asignan ahora en `get_current_user`. `get_scoped_db` quedó eliminado. Migración `0010`
   agrega el bypass explícito del rol `cliente` en las políticas RLS.

## Pendientes

### 1. Rediseño de la interfaz, fases 1 y 2 (en curso)

Spec: `docs/superpowers/specs/2026-09-20-auth-frontend-y-rediseno-ui-design.md`.

Hecho (`c770b24`, `8db0890`):

- Los tres bugs de autorización del frontend. `AuthGuard` acepta `roles`, el mapa de rutas
  vive en `lib/rutas.ts` derivado de `require_roles` del backend, y un rol no permitido ve
  una pantalla explicativa. Se quitó el chequeo de rol duplicado que traían seis páginas.
- `logout` sigue puro y la navegación es explícita en quien lo llama.
- Sistema de tokens en dos capas, con paleta oscura definida pero no activada.
- `AppShell` con `Sidebar`: permanente desde 1024px, drawer en móvil, secciones filtradas
  por rol contra la misma fuente que el guard. `NavBar` eliminado.

Pendiente:

- Nueve componentes compartidos en `components/ui/`: `Button`, `Field`, `Card`,
  `DataTable`, `Badge`, `EmptyState`, `Skeleton`, `Alert`, `PageHeader`.
- Migrar las páginas piloto `/login`, `/patios` y `/contenedores`, y después las once
  restantes.
- Borrar los alias temporales de variables CSS de `globals.css` cuando ya nadie los use.

El fallo intermitente del formulario de login **sigue sin causa raíz**. En una prueba el
clic en "Entrar" no produjo ninguna petición HTTP. Se instrumentó para distinguir un fallo
de red de uno de credenciales, pero no se ha reproducido desde entonces.

### 2. Flujo de QR (no diseñado)

Los estados `qr_ingreso_emitido`, `qr_salida_emitido` y `en_porteria_salida` existen en el
enum pero ningún endpoint los produce. Falta la spec del QR, tanto de entrada como de salida.
La transición automática de `solicitud_salida` a `despachado` depende de este flujo.

### 3. Fuera de alcance acumulado en las specs

De Spec 1:
- Rutina inteligente de asignación de patio por lleno/vacío.
- Reenvío del código de verificación como acción explícita.
- Rate limiting y protección anti-abuso en `registro` y `verificar`.

De Spec 2 (PIN):
- Gate en `POST /movimientos` que impida ubicar un contenedor sin PIN verificado.
- Límite de reintentos o bloqueo por PIN incorrecto repetido.
- Constraint de unicidad sobre `numero_contenedor` en contenedores activos.

De la spec de solicitud de salida:
- Cálculo de capacidad de grúa por día o turno.
- Estados `en_estadia` y `en_servicio_especial`.
- Cancelar o modificar una solicitud de salida ya creada.
- Edición de `nombre`, `codigo` y `activo` de `Patio` (el PATCH actual solo cubre la
  anticipación mínima).

De la spec del fix de RLS:
- Rediseñar las políticas RLS para filtrar por `cliente_id` en vez de dar bypass total al
  rol `cliente`. Hoy la autorización por dueño vive en Python, endpoint por endpoint.

### 4. Nunca abordado

- PWA offline para la operación en patio.
- Mapa SVG interactivo del patio.
- CRUD de geocercas.
- API pública para socios (`socio_api` ya existe como tipo de cliente).

## Deuda técnica conocida

- Las políticas RLS conservan el bypass `IS NULL`. Es intencional: permite que el código que
  toca la base de datos sin pasar por el middleware HTTP (tests directos de ORM, scripts)
  siga funcionando. El riesgo es que en producción un camino que no pase por
  `get_current_user` queda sin filtro.
- Los GUC personalizados de PostgreSQL (`app.*`) se inicializan permanentemente a cadena
  vacía en cuanto se tocan por primera vez. No vuelven a `NULL` con `ROLLBACK`, `RESET` ni
  con una sesión nueva de SQLAlchemy sobre la misma conexión física. Cualquier código que
  asigne GUC debe hacerlo en todos los requests, no solo en algunos.
- No existe endpoint de alta del primer usuario admin. Se siembra manualmente con `psql`.
- Los roles `guardia` y `despachador` existen en `RolUsuario` pero ningún endpoint los
  acepta para escribir. Un usuario con esos roles se autentica y no puede hacer nada, ni
  tiene una sola ruta propia en la navegación.
- `globals.css` conserva alias temporales de los nombres viejos de variables
  (`--azul`, `--surface`, `--border`, ...) porque las páginas sin migrar los usan. Se
  borran al cerrar la Fase 2 del rediseño.
- Las casillas de verificación de los planes en `docs/superpowers/plans/` nunca se marcaron.
  No sirven para saber qué está hecho. El historial de git es la fuente confiable.

## Desarrollo local

```bash
# Base de datos
docker compose up -d          # Postgres en :5433

# Backend
cd backend
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload --port 8000
pytest

# Frontend
cd frontend
npm install
npm run dev                   # :3000
npx vitest run
```

Variables requeridas en `backend/.env`: `DATABASE_URL`, `MIGRATIONS_DATABASE_URL`,
`JWT_SECRET`. En `frontend/.env.local`: `NEXT_PUBLIC_API_URL`.

## Cómo se trabaja aquí

Cada feature arranca con un documento de diseño en `docs/superpowers/specs/`, seguido de un
plan paso a paso en `docs/superpowers/plans/`. La implementación va task por task con TDD:
test que falla, implementación, test verde, commit. Los mensajes de commit siguen
Conventional Commits en español y sin acentos.
