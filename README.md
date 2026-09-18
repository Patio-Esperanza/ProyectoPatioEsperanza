# Patio Esperanza

Sistema interno de gestión de patio de contenedores: control de ingreso, ubicación, movimientos y salida de contenedores por patio, con roles internos (operador, supervisor, admin).

## Stack

**Backend** (`backend/`)
- FastAPI + SQLAlchemy 2.0 (async) + asyncpg
- PostgreSQL 16, migraciones con Alembic
- Auth JWT (PyJWT + passlib/bcrypt)
- Row-Level Security por `patio_id` a nivel de base de datos
- Tests con pytest + pytest-asyncio + httpx

**Frontend** (`frontend/`)
- Next.js 14 (App Router) + TypeScript, componentes cliente
- Sesión JWT en `localStorage`, sin librería de UI externa
- CSS Modules + variables CSS (paleta de marca)
- Tests con Vitest + React Testing Library

**Infra**
- Despliegue en DigitalOcean App Platform (`app.yaml`): servicio `api` (FastAPI), `web` (Next.js), `background-jobs` (worker), base de datos administrada
- Desarrollo local con Docker Compose (Postgres)

## Estructura

```
backend/    API FastAPI (app/, alembic/, tests/)
frontend/   Dashboard Next.js (app/, components/, lib/)
docs/       Planes de implementación (docs/superpowers/plans/)
docker/     Scripts de inicialización de base de datos
img/        Assets de marca (logo, favicon)
app.yaml    Especificación de despliegue (DigitalOcean App Platform)
```

## Desarrollo local

### Requisitos
- Node.js v20.20.2 (gestionado con nvm)
- Python 3.12
- Docker (para Postgres local)

### Base de datos

```bash
docker compose up -d db
```

Levanta Postgres 16 en `localhost:5433` (usuario/clave `patio`, base `patio_dev`).

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Crear `backend/.env`:

```
DATABASE_URL=postgresql+asyncpg://patio_app:patio_app@localhost:5433/patio_dev
MIGRATIONS_DATABASE_URL=postgresql+asyncpg://patio:patio@localhost:5433/patio_dev
JWT_SECRET=<secreto local>
```

Aplicar migraciones y levantar la API:

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Correr tests:

```bash
pytest
```

### Frontend

```bash
cd frontend
npm install
```

Crear `frontend/.env.local` (ver `.env.local.example`):

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

```bash
npm run dev     # servidor de desarrollo en :3000
npm test        # suite Vitest
npm run build   # build de producción
```

No existe endpoint de alta de usuarios: el primer usuario admin se siembra manualmente vía `psql` contra `patio_dev`.

## API

Endpoints principales expuestos por el backend (`backend/app/api/routes/`):

| Ruta | Descripción |
|---|---|
| `POST /api/auth/login` | Login, devuelve JWT |
| `GET /api/health`, `/api/health/db` | Healthchecks |
| `GET /api/patios`, `POST /api/patios` | Listar / crear patios (crear: admin) |
| `POST /api/contenedores`, `GET /api/contenedores/{id}` | Alta de contenedor (validación ISO 6346) / detalle |
| `POST /api/movimientos` | Registrar movimiento (ingreso/reubicación/servicio/salida), con locking de slot |
| `POST /api/ubicaciones/sugerir` | Sugerencia de ubicación por algoritmo de scoring |

El rol y los patios asignados a un usuario se leen del propio JWT (`sub`, `rol`, `patios`); no hay endpoint `/me`.

## Estado del proyecto

Implementado (ver `docs/superpowers/plans/`):
- Backend: auth, CRUD de patios, CRUD de contenedores con validación ISO 6346 y auditoría, movimientos con locking de slot y máquina de estados, algoritmo de sugerencia de ubicación, Row-Level Security por `patio_id`.
- Frontend: login, navegación con guard de sesión, patios, contenedores (alta + detalle), movimientos, sugerencia de ubicación.

Fuera de alcance actual (requieren endpoints de backend que no existen todavía): portal cliente (solicitudes, QR), flujo de portería, PWA offline, mapa SVG interactivo, CRUD de usuarios/geocercas, API de socios.

## Contribuir

Los cambios se implementan siguiendo planes en `docs/superpowers/plans/`, task por task con TDD (test que falla → implementación → test verde → commit).
