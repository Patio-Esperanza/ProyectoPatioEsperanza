# Gestión de Usuarios Internos + Auto-relleno de Patio — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que un admin cree y liste usuarios internos (operador/supervisor/guardia/despachador/admin) con sus patios asignados, y reemplazar el input de texto libre de `patio_id` en `Contenedores` (crear) y `Sugerir ubicación` por un selector que solo ofrece los patios del usuario logueado.

**Architecture:** Backend: nuevo router `usuarios.py` (mismo patrón que `patios.py`/`contenedores.py`: `require_roles`, `registrar_auditoria`, sin relaciones ORM — se arma la respuesta a mano igual que el resto del código). Frontend: nuevo hook `usePatiosDisponibles` (filtra `listPatios()` contra el rol/patios del usuario) reutilizado por un componente `PatioSelect` (select que se autoselecciona y bloquea si hay un solo patio) y por la nueva página `/usuarios`.

**Tech Stack:** FastAPI + SQLAlchemy async + Pydantic (backend), Next.js 14 + TypeScript + Vitest/RTL (frontend). Sin dependencias nuevas.

## Global Constraints

- Roles asignables desde `/usuarios`: `operador`, `supervisor`, `guardia`, `despachador`, `admin` (no `cliente`, es del portal externo, fuera de alcance).
- `email` duplicado → `409 Conflict`, mensaje `"Email ya registrado"`.
- `password` con menos de 8 caracteres → `422` (validación Pydantic estándar).
- `tipo` distinto de `admin` con `patio_ids` vacío → `422`, mensaje `"Este rol requiere al menos un patio asignado"`.
- `patio_ids` con algún id que no existe en `patios` → `422`, mensaje `"Uno o mas patio_ids no existen"`.
- `tipo == cliente` en el payload → `422`, mensaje `"El rol cliente no se crea desde este endpoint"`.
- `GET /api/usuarios` y `POST /api/usuarios`: solo rol `admin` (`require_roles(RolUsuario.ADMIN)`).
- `Movimientos` no tiene campo `patio_id` en su payload — no se toca en este plan.
- Ningún endpoint nuevo de listado de contenedores/ubicaciones — `contenedor_id`/`ubicacion_destino_id` siguen siendo UUID escritos a mano (limitación conocida, fuera de alcance).

---

## File Structure

```
backend/
├── app/
│   ├── main.py                          # MODIFICAR: registrar router usuarios
│   ├── schemas/
│   │   └── usuario.py                   # NUEVO: UsuarioCreate, UsuarioOut
│   └── api/routes/
│       └── usuarios.py                  # NUEVO: POST/GET /api/usuarios
└── tests/
    └── test_usuarios_api.py             # NUEVO

frontend/
├── lib/
│   ├── api.ts                           # MODIFICAR: Usuario, RolUsuario, listUsuarios, createUsuario
│   ├── api.test.ts                      # MODIFICAR
│   ├── use-patios-disponibles.ts        # NUEVO
│   └── use-patios-disponibles.test.ts   # NUEVO
├── components/
│   ├── PatioSelect.tsx                  # NUEVO
│   ├── PatioSelect.test.tsx             # NUEVO
│   ├── NavBar.tsx                       # MODIFICAR: link "Usuarios" solo admin
│   └── NavBar.test.tsx                  # MODIFICAR
└── app/
    ├── usuarios/
    │   ├── page.tsx                     # NUEVO
    │   ├── page.module.css              # NUEVO
    │   └── page.test.tsx                # NUEVO
    ├── contenedores/
    │   ├── page.tsx                     # MODIFICAR: patio_id input -> PatioSelect
    │   └── page.test.tsx                # MODIFICAR
    └── ubicaciones/sugerir/
        ├── page.tsx                     # MODIFICAR: patio_id input -> PatioSelect
        └── page.test.tsx                # MODIFICAR
```

---

### Task 1: Backend — `POST /api/usuarios` y `GET /api/usuarios`

**Files:**
- Create: `backend/app/schemas/usuario.py`
- Create: `backend/app/api/routes/usuarios.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_usuarios_api.py`

**Interfaces:**
- Produces: `POST /api/usuarios` (admin-only, 201) y `GET /api/usuarios` (admin-only, 200) devolviendo `UsuarioOut { id, nombre, email, tipo, activo, patios: PatioOut[] }`. Consumidos por Tasks 2-7 (vía `lib/api.ts`).
- Consumes: `require_roles`, `CurrentUser` (`app/api/deps.py`), `registrar_auditoria` (`app/core/auditoria.py`), `hash_password` (`app/core/security.py`), `Patio` (`app/models/ubicacion.py`), `Usuario`/`UsuarioPatio` (`app/models/usuario.py`), `PatioOut` (`app/schemas/patio.py`) — todo ya existente.

- [ ] **Step 1: Escribir tests que fallan**

`backend/tests/test_usuarios_api.py`:

```python
import uuid

import pytest

from app.core.security import create_access_token
from app.models.enums import RolUsuario
from app.models.ubicacion import Patio
from app.models.usuario import Usuario

_USUARIO_ID = "00000000-0000-0000-0000-000000000001"


def _token(rol: RolUsuario, patios: list[str] | None = None) -> str:
    return create_access_token(_USUARIO_ID, rol.value, patios or [], 60)


async def _crear_usuario_autenticado(db_session, rol: RolUsuario) -> None:
    db_session.add(
        Usuario(
            id=uuid.UUID(_USUARIO_ID),
            tipo=rol,
            email=f"{rol.value}@patio.mx",
            password_hash="hash",
            activo=True,
        )
    )
    await db_session.commit()


async def _crear_patio(db_session, nombre: str, codigo: str) -> uuid.UUID:
    patio = Patio(nombre=nombre, codigo=codigo)
    db_session.add(patio)
    await db_session.commit()
    await db_session.refresh(patio)
    return patio.id


@pytest.mark.anyio
async def test_admin_crea_usuario_con_patios(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    patio_id = await _crear_patio(db_session, "Patio Norte", "PN")
    token = _token(RolUsuario.ADMIN)

    response = await client.post(
        "/api/usuarios",
        json={
            "nombre": "Juan Operador",
            "email": "juan@patio.mx",
            "password": "clave1234",
            "tipo": "operador",
            "patio_ids": [str(patio_id)],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "juan@patio.mx"
    assert body["tipo"] == "operador"
    assert [p["codigo"] for p in body["patios"]] == ["PN"]


@pytest.mark.anyio
async def test_operador_no_puede_crear_usuario(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.OPERADOR)
    token = _token(RolUsuario.OPERADOR)

    response = await client.post(
        "/api/usuarios",
        json={
            "nombre": "Otro",
            "email": "otro@patio.mx",
            "password": "clave1234",
            "tipo": "operador",
            "patio_ids": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_email_duplicado_devuelve_409(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    patio_id = await _crear_patio(db_session, "Patio Norte", "PN")
    token = _token(RolUsuario.ADMIN)
    payload = {
        "nombre": "Juan",
        "email": "duplicado@patio.mx",
        "password": "clave1234",
        "tipo": "operador",
        "patio_ids": [str(patio_id)],
    }

    primera = await client.post(
        "/api/usuarios", json=payload, headers={"Authorization": f"Bearer {token}"}
    )
    assert primera.status_code == 201

    segunda = await client.post(
        "/api/usuarios", json=payload, headers={"Authorization": f"Bearer {token}"}
    )
    assert segunda.status_code == 409


@pytest.mark.anyio
async def test_rol_no_admin_sin_patios_devuelve_422(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)

    response = await client.post(
        "/api/usuarios",
        json={
            "nombre": "Sin Patio",
            "email": "sinpatio@patio.mx",
            "password": "clave1234",
            "tipo": "supervisor",
            "patio_ids": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_admin_puede_crearse_sin_patios(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)

    response = await client.post(
        "/api/usuarios",
        json={
            "nombre": "Otro Admin",
            "email": "otroadmin@patio.mx",
            "password": "clave1234",
            "tipo": "admin",
            "patio_ids": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["patios"] == []


@pytest.mark.anyio
async def test_listar_usuarios_incluye_patios(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    patio_id = await _crear_patio(db_session, "Patio Sur", "PS")
    token = _token(RolUsuario.ADMIN)
    await client.post(
        "/api/usuarios",
        json={
            "nombre": "Ana",
            "email": "ana@patio.mx",
            "password": "clave1234",
            "tipo": "supervisor",
            "patio_ids": [str(patio_id)],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    response = await client.get("/api/usuarios", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    ana = next(u for u in response.json() if u["email"] == "ana@patio.mx")
    assert [p["codigo"] for p in ana["patios"]] == ["PS"]
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_usuarios_api.py -v
```
Esperado: FAIL — `404 Not Found` en todas (la ruta `/api/usuarios` no existe todavía).

- [ ] **Step 3: `backend/app/schemas/usuario.py`**

```python
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RolUsuario
from app.schemas.patio import PatioOut


class UsuarioCreate(BaseModel):
    nombre: str
    email: str
    password: str = Field(min_length=8)
    tipo: RolUsuario
    patio_ids: list[uuid.UUID] = []


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str | None
    email: str
    tipo: RolUsuario
    activo: bool
    patios: list[PatioOut] = []
```

- [ ] **Step 4: `backend/app/api/routes/usuarios.py`**

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.core.auditoria import registrar_auditoria
from app.core.security import hash_password
from app.db import get_db
from app.models.enums import RolUsuario
from app.models.ubicacion import Patio
from app.models.usuario import Usuario, UsuarioPatio
from app.schemas.patio import PatioOut
from app.schemas.usuario import UsuarioCreate, UsuarioOut

router = APIRouter()


async def _patios_por_usuario(
    db: AsyncSession, usuario_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[PatioOut]]:
    if not usuario_ids:
        return {}
    result = await db.execute(
        select(UsuarioPatio.usuario_id, Patio)
        .join(Patio, Patio.id == UsuarioPatio.patio_id)
        .where(UsuarioPatio.usuario_id.in_(usuario_ids))
    )
    agrupado: dict[uuid.UUID, list[PatioOut]] = {}
    for usuario_id, patio in result.all():
        agrupado.setdefault(usuario_id, []).append(PatioOut.model_validate(patio))
    return agrupado


def _a_usuario_out(usuario: Usuario, patios: list[PatioOut]) -> UsuarioOut:
    return UsuarioOut(
        id=usuario.id,
        nombre=usuario.nombre,
        email=usuario.email,
        tipo=usuario.tipo,
        activo=usuario.activo,
        patios=patios,
    )


@router.post("", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    payload: UsuarioCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.ADMIN)),
) -> UsuarioOut:
    if payload.tipo == RolUsuario.CLIENTE:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "El rol cliente no se crea desde este endpoint",
        )

    if payload.tipo != RolUsuario.ADMIN and not payload.patio_ids:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Este rol requiere al menos un patio asignado",
        )

    existente = await db.execute(select(Usuario).where(Usuario.email == payload.email))
    if existente.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email ya registrado")

    patios_out: list[PatioOut] = []
    if payload.patio_ids:
        patios_result = await db.execute(select(Patio).where(Patio.id.in_(payload.patio_ids)))
        patios_encontrados = list(patios_result.scalars().all())
        if {p.id for p in patios_encontrados} != set(payload.patio_ids):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "Uno o mas patio_ids no existen"
            )
        patios_out = [PatioOut.model_validate(p) for p in patios_encontrados]

    usuario = Usuario(
        nombre=payload.nombre,
        email=payload.email,
        password_hash=hash_password(payload.password),
        tipo=payload.tipo,
        activo=True,
    )
    db.add(usuario)
    await db.flush()

    for patio_id in payload.patio_ids:
        db.add(UsuarioPatio(usuario_id=usuario.id, patio_id=patio_id))
    await db.flush()

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="crear",
        entidad="usuarios",
        entidad_id=str(usuario.id),
        valor_anterior=None,
        valor_nuevo={"email": usuario.email, "tipo": usuario.tipo.value},
        patio_id=payload.patio_ids[0] if payload.patio_ids else None,
    )
    await db.commit()

    return _a_usuario_out(usuario, patios_out)


@router.get("", response_model=list[UsuarioOut])
async def listar_usuarios(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.ADMIN)),
) -> list[UsuarioOut]:
    result = await db.execute(select(Usuario))
    usuarios = list(result.scalars().all())
    patios_por_usuario = await _patios_por_usuario(db, [u.id for u in usuarios])
    return [_a_usuario_out(u, patios_por_usuario.get(u.id, [])) for u in usuarios]
```

- [ ] **Step 5: Registrar el router en `backend/app/main.py`**

Modificar el bloque de imports y de `include_router`:

```python
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import auth, contenedores, movimientos, patios, ubicaciones, usuarios
from app.config import settings
from app.db import get_db

app = FastAPI(title="Patio Esperanza API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health/db")
async def health_db(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(patios.router, prefix="/api/patios", tags=["patios"])
app.include_router(contenedores.router, prefix="/api/contenedores", tags=["contenedores"])
app.include_router(movimientos.router, prefix="/api/movimientos", tags=["movimientos"])
app.include_router(ubicaciones.router, prefix="/api/ubicaciones", tags=["ubicaciones"])
app.include_router(usuarios.router, prefix="/api/usuarios", tags=["usuarios"])
```

- [ ] **Step 6: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_usuarios_api.py -v
```
Esperado: PASS (6 tests)

- [ ] **Step 7: Correr la suite completa de backend**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest -q
```
Esperado: PASS (41 tests — 35 previos + 6 nuevos)

- [ ] **Step 8: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/schemas/usuario.py backend/app/api/routes/usuarios.py \
  backend/app/main.py backend/tests/test_usuarios_api.py
git commit -m "feat: endpoint de alta y listado de usuarios internos"
```

---

### Task 2: Frontend — cliente HTTP para usuarios (`lib/api.ts`)

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/api.test.ts`

**Interfaces:**
- Produces: `RolUsuario = "operador" | "supervisor" | "admin" | "guardia" | "despachador"`, `Usuario { id, nombre: string | null, email, tipo: RolUsuario, activo, patios: Patio[] }`, `listUsuarios(token) -> Promise<Usuario[]>`, `createUsuario(token, { nombre, email, password, tipo, patio_ids: string[] }) -> Promise<Usuario>`. Consumidos por Tasks 3 y 7.
- Consumes: `request`, `ApiError`, `Patio` (ya existentes en `lib/api.ts`, Tasks 2 y 5 del plan de frontend original).

- [ ] **Step 1: Escribir tests que fallan**

Agregar a `frontend/lib/api.test.ts` (agregar `listUsuarios, createUsuario, type Usuario` al import existente desde `"./api"`, y este bloque al final del archivo):

```ts
const USUARIO: Usuario = {
  id: "u1",
  nombre: "Juan Operador",
  email: "juan@patio.mx",
  tipo: "operador",
  activo: true,
  patios: [{ id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true }],
};

describe("listUsuarios", () => {
  it("sends the bearer token and returns the list", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => [USUARIO] });

    const result = await listUsuarios("token-123");

    expect(result).toEqual([USUARIO]);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/usuarios");
    expect(options.headers.Authorization).toBe("Bearer token-123");
  });
});

describe("createUsuario", () => {
  it("posts the payload as JSON with the bearer token", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 201, json: async () => USUARIO });

    const result = await createUsuario("token-123", {
      nombre: "Juan Operador",
      email: "juan@patio.mx",
      password: "clave1234",
      tipo: "operador",
      patio_ids: ["p1"],
    });

    expect(result).toEqual(USUARIO);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/usuarios");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body as string)).toEqual({
      nombre: "Juan Operador",
      email: "juan@patio.mx",
      password: "clave1234",
      tipo: "operador",
      patio_ids: ["p1"],
    });
  });
});
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- lib/api.test.ts
```
Esperado: FAIL — `listUsuarios`/`createUsuario`/`Usuario` no existen en `./api`.

- [ ] **Step 3: Agregar a `frontend/lib/api.ts`** (al final del archivo)

```ts
export type RolUsuario = "operador" | "supervisor" | "admin" | "guardia" | "despachador";

export interface Usuario {
  id: string;
  nombre: string | null;
  email: string;
  tipo: RolUsuario;
  activo: boolean;
  patios: Patio[];
}

export async function listUsuarios(token: string): Promise<Usuario[]> {
  return request<Usuario[]>("/api/usuarios", { token });
}

export async function createUsuario(
  token: string,
  payload: {
    nombre: string;
    email: string;
    password: string;
    tipo: RolUsuario;
    patio_ids: string[];
  }
): Promise<Usuario> {
  return request<Usuario>("/api/usuarios", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}
```

- [ ] **Step 4: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- lib/api.test.ts
```
Esperado: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/lib/api.ts frontend/lib/api.test.ts
git commit -m "feat: cliente HTTP para usuarios (listUsuarios, createUsuario)"
```

---

### Task 3: Frontend — hook `usePatiosDisponibles`

**Files:**
- Create: `frontend/lib/use-patios-disponibles.ts`
- Test: `frontend/lib/use-patios-disponibles.test.ts`

**Interfaces:**
- Produces: `usePatiosDisponibles() -> { patios: Patio[]; loading: boolean }`. Consumido por Tasks 4 y 7.
- Consumes: `useAuth` (`lib/auth-context.tsx`), `listPatios`, `type Patio` (`lib/api.ts`).

- [ ] **Step 1: Escribir test que falla**

`frontend/lib/use-patios-disponibles.test.ts`:

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { usePatiosDisponibles } from "./use-patios-disponibles";
import { useAuth } from "./auth-context";
import { listPatios } from "./api";

vi.mock("./auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("./api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api")>();
  return { ...actual, listPatios: vi.fn() };
});

const PATIOS = [
  { id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true },
  { id: "p2", nombre: "Patio Sur", codigo: "PS", activo: true },
];

beforeEach(() => {
  vi.mocked(listPatios).mockReset();
});

describe("usePatiosDisponibles", () => {
  it("returns all patios for an admin", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "admin", patios: [] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });
    vi.mocked(listPatios).mockResolvedValue(PATIOS);

    const { result } = renderHook(() => usePatiosDisponibles());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.patios).toEqual(PATIOS);
  });

  it("filters to only the user's assigned patios for non-admin roles", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "operador", patios: ["p2"] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });
    vi.mocked(listPatios).mockResolvedValue(PATIOS);

    const { result } = renderHook(() => usePatiosDisponibles());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.patios).toEqual([PATIOS[1]]);
  });
});
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- lib/use-patios-disponibles.test.ts
```
Esperado: FAIL — `Cannot find module './use-patios-disponibles'`

- [ ] **Step 3: `frontend/lib/use-patios-disponibles.ts`**

```ts
"use client";

import { useEffect, useState } from "react";
import { useAuth } from "./auth-context";
import { listPatios, type Patio } from "./api";

export interface PatiosDisponibles {
  patios: Patio[];
  loading: boolean;
}

export function usePatiosDisponibles(): PatiosDisponibles {
  const { token, user } = useAuth();
  const [patios, setPatios] = useState<Patio[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token || !user) return;
    let cancelado = false;
    listPatios(token)
      .then((todos) => {
        if (cancelado) return;
        const disponibles =
          user.rol === "admin" ? todos : todos.filter((patio) => user.patios.includes(patio.id));
        setPatios(disponibles);
      })
      .finally(() => {
        if (!cancelado) setLoading(false);
      });
    return () => {
      cancelado = true;
    };
  }, [token, user]);

  return { patios, loading };
}
```

- [ ] **Step 4: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- lib/use-patios-disponibles.test.ts
```
Esperado: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/lib/use-patios-disponibles.ts frontend/lib/use-patios-disponibles.test.ts
git commit -m "feat: hook usePatiosDisponibles"
```

---

### Task 4: Frontend — componente `PatioSelect`

**Files:**
- Create: `frontend/components/PatioSelect.tsx`
- Test: `frontend/components/PatioSelect.test.tsx`

**Interfaces:**
- Produces: `PatioSelect({ id, value, onChange }: { id: string; value: string; onChange: (patioId: string) => void })`. Consumido por Tasks 5 y 6.
- Consumes: `usePatiosDisponibles` (Task 3).

- [ ] **Step 1: Escribir test que falla**

`frontend/components/PatioSelect.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PatioSelect } from "./PatioSelect";
import { usePatiosDisponibles } from "@/lib/use-patios-disponibles";

vi.mock("@/lib/use-patios-disponibles", () => ({ usePatiosDisponibles: vi.fn() }));

beforeEach(() => {
  vi.mocked(usePatiosDisponibles).mockReset();
});

describe("PatioSelect", () => {
  it("shows a loading message while patios load", () => {
    vi.mocked(usePatiosDisponibles).mockReturnValue({ patios: [], loading: true });

    render(<PatioSelect id="patio_id" value="" onChange={vi.fn()} />);

    expect(screen.getByText("Cargando patios...")).toBeInTheDocument();
  });

  it("shows a message when there are no patios available", () => {
    vi.mocked(usePatiosDisponibles).mockReturnValue({ patios: [], loading: false });

    render(<PatioSelect id="patio_id" value="" onChange={vi.fn()} />);

    expect(screen.getByText("No tienes patios asignados.")).toBeInTheDocument();
  });

  it("auto-selects and disables the select when there is exactly one patio", () => {
    const onChange = vi.fn();
    vi.mocked(usePatiosDisponibles).mockReturnValue({
      patios: [{ id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true }],
      loading: false,
    });

    render(<PatioSelect id="patio_id" value="" onChange={onChange} />);

    expect(onChange).toHaveBeenCalledWith("p1");
    expect(screen.getByRole("combobox")).toBeDisabled();
  });

  it("lets the user pick among multiple patios", async () => {
    const onChange = vi.fn();
    vi.mocked(usePatiosDisponibles).mockReturnValue({
      patios: [
        { id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true },
        { id: "p2", nombre: "Patio Sur", codigo: "PS", activo: true },
      ],
      loading: false,
    });

    const user = userEvent.setup();
    render(<PatioSelect id="patio_id" value="" onChange={onChange} />);

    expect(screen.getByRole("combobox")).not.toBeDisabled();
    await user.selectOptions(screen.getByRole("combobox"), "p2");
    expect(onChange).toHaveBeenCalledWith("p2");
  });
});
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- components/PatioSelect.test.tsx
```
Esperado: FAIL — `Cannot find module './PatioSelect'`

- [ ] **Step 3: `frontend/components/PatioSelect.tsx`**

```tsx
"use client";

import { useEffect } from "react";
import { usePatiosDisponibles } from "@/lib/use-patios-disponibles";

interface PatioSelectProps {
  id: string;
  value: string;
  onChange: (patioId: string) => void;
}

export function PatioSelect({ id, value, onChange }: PatioSelectProps) {
  const { patios, loading } = usePatiosDisponibles();

  useEffect(() => {
    if (patios.length === 1 && value !== patios[0].id) {
      onChange(patios[0].id);
    }
  }, [patios, value, onChange]);

  if (loading) return <p>Cargando patios...</p>;
  if (patios.length === 0) return <p>No tienes patios asignados.</p>;

  return (
    <select
      id={id}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={patios.length === 1}
      required
    >
      {patios.length > 1 && <option value="">Selecciona un patio</option>}
      {patios.map((patio) => (
        <option key={patio.id} value={patio.id}>
          {patio.nombre} ({patio.codigo})
        </option>
      ))}
    </select>
  );
}
```

- [ ] **Step 4: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- components/PatioSelect.test.tsx
```
Esperado: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/components/PatioSelect.tsx frontend/components/PatioSelect.test.tsx
git commit -m "feat: componente PatioSelect con auto-seleccion"
```

---

### Task 5: Frontend — auto-relleno de patio en Contenedores (crear)

**Files:**
- Modify: `frontend/app/contenedores/page.tsx`
- Modify: `frontend/app/contenedores/page.test.tsx`

**Interfaces:**
- Consumes: `PatioSelect` (Task 4).

- [ ] **Step 1: Reemplazar `frontend/app/contenedores/page.test.tsx`** (test que falla contra la implementación actual, que todavía usa `<input>`)

```tsx
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ContenedoresPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { createContenedor, listPatios } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, createContenedor: vi.fn(), listPatios: vi.fn() };
});

const PATIOS = [
  { id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true },
  { id: "p2", nombre: "Patio Sur", codigo: "PS", activo: true },
];

beforeEach(() => {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "1", rol: "operador", patios: ["p1", "p2"] },
    token: "token",
    ready: true,
    setToken: vi.fn(),
    logout: vi.fn(),
  });
  vi.mocked(createContenedor).mockReset();
  vi.mocked(listPatios).mockReset();
  vi.mocked(listPatios).mockResolvedValue(PATIOS);
});

describe("ContenedoresPage", () => {
  it("creates a contenedor with the form values", async () => {
    vi.mocked(createContenedor).mockResolvedValue({
      id: "c1",
      numero_contenedor: "CSQU3054383",
      tipo: "lleno",
      tamano: "40",
      patio_id: "p1",
      estado: "solicitud_ingreso",
      peso_kg: 18000,
    });

    const user = userEvent.setup();
    render(<ContenedoresPage />);

    await user.type(screen.getByLabelText("Número de contenedor"), "CSQU3054383");
    await user.selectOptions(await screen.findByLabelText("Patio"), "p1");
    await user.type(screen.getByLabelText("Peso (kg)"), "18000");
    await user.click(screen.getByRole("button", { name: "Crear contenedor" }));

    expect(createContenedor).toHaveBeenCalledWith("token", {
      numero_contenedor: "CSQU3054383",
      tipo: "lleno",
      tamano: "40",
      patio_id: "p1",
      peso_kg: 18000,
    });
    expect(await screen.findByText(/estado solicitud_ingreso/)).toBeInTheDocument();
  });

  it("shows the backend error message on failure", async () => {
    const { ApiError } = await import("@/lib/api");
    vi.mocked(createContenedor).mockRejectedValue(
      new ApiError(422, "numero_contenedor no cumple el checksum ISO 6346")
    );

    const user = userEvent.setup();
    render(<ContenedoresPage />);

    await user.type(screen.getByLabelText("Número de contenedor"), "CSQU3054380");
    await user.selectOptions(await screen.findByLabelText("Patio"), "p1");
    await user.type(screen.getByLabelText("Peso (kg)"), "18000");
    await user.click(screen.getByRole("button", { name: "Crear contenedor" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "numero_contenedor no cumple el checksum ISO 6346"
    );
  });

  it("auto-selects and locks the patio when the user has only one assigned", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "operador", patios: ["p1"] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    render(<ContenedoresPage />);

    const select = await screen.findByLabelText("Patio");
    expect(select).toBeDisabled();
    expect(select).toHaveValue("p1");
  });
});
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/contenedores/page.test.tsx
```
Esperado: FAIL — `getByLabelText("Patio")` no encuentra nada (la página actual usa el label "ID de patio" con un `<input>`).

- [ ] **Step 3: Modificar `frontend/app/contenedores/page.tsx`**

Reemplazar el import y el bloque del campo de patio. El import pasa de:

```tsx
import { AuthGuard } from "@/components/AuthGuard";
```

a:

```tsx
import { AuthGuard } from "@/components/AuthGuard";
import { PatioSelect } from "@/components/PatioSelect";
```

Y el bloque:

```tsx
        <label htmlFor="patio_id">ID de patio</label>
        <input id="patio_id" value={patioId} onChange={(e) => setPatioId(e.target.value)} required />
```

se reemplaza por:

```tsx
        <label htmlFor="patio_id">Patio</label>
        <PatioSelect id="patio_id" value={patioId} onChange={setPatioId} />
```

El resto del archivo (estado `patioId`/`setPatioId`, el resto del formulario, `ContenedoresPage`) no cambia.

- [ ] **Step 4: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/contenedores/page.test.tsx
```
Esperado: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/app/contenedores/page.tsx frontend/app/contenedores/page.test.tsx
git commit -m "feat: auto-relleno de patio en alta de contenedores"
```

---

### Task 6: Frontend — auto-relleno de patio en Sugerir ubicación

**Files:**
- Modify: `frontend/app/ubicaciones/sugerir/page.tsx`
- Modify: `frontend/app/ubicaciones/sugerir/page.test.tsx`

**Interfaces:**
- Consumes: `PatioSelect` (Task 4).

- [ ] **Step 1: Reemplazar `frontend/app/ubicaciones/sugerir/page.test.tsx`**

```tsx
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SugerirUbicacionPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { sugerirUbicacion, listPatios } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, sugerirUbicacion: vi.fn(), listPatios: vi.fn() };
});

const PATIOS = [
  { id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true },
  { id: "p2", nombre: "Patio Sur", codigo: "PS", activo: true },
];

beforeEach(() => {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "1", rol: "operador", patios: ["p1", "p2"] },
    token: "token",
    ready: true,
    setToken: vi.fn(),
    logout: vi.fn(),
  });
  vi.mocked(sugerirUbicacion).mockReset();
  vi.mocked(listPatios).mockReset();
  vi.mocked(listPatios).mockResolvedValue(PATIOS);
});

describe("SugerirUbicacionPage", () => {
  it("shows the suggested slot and its cost", async () => {
    vi.mocked(sugerirUbicacion).mockResolvedValue({
      ubicacion_id: "u1",
      codigo: "A1-T1-S1-N1",
      costo: 1.3,
    });

    const user = userEvent.setup();
    render(<SugerirUbicacionPage />);

    await user.selectOptions(await screen.findByLabelText("Patio"), "p1");
    await user.type(screen.getByLabelText("ID de contenedor"), "c1");
    await user.type(screen.getByLabelText("ID de ubicación de referencia"), "u0");
    await user.click(screen.getByRole("button", { name: "Sugerir" }));

    expect(sugerirUbicacion).toHaveBeenCalledWith("token", {
      patio_id: "p1",
      contenedor_id: "c1",
      punto_referencia_ubicacion_id: "u0",
    });
    expect(await screen.findByText(/A1-T1-S1-N1/)).toBeInTheDocument();
    expect(screen.getByText(/costo 1.30/)).toBeInTheDocument();
  });

  it("shows the backend error when there is no valid slot", async () => {
    const { ApiError } = await import("@/lib/api");
    vi.mocked(sugerirUbicacion).mockRejectedValue(
      new ApiError(409, "No hay ubicaciones disponibles que cumplan las restricciones")
    );

    const user = userEvent.setup();
    render(<SugerirUbicacionPage />);

    await user.selectOptions(await screen.findByLabelText("Patio"), "p1");
    await user.type(screen.getByLabelText("ID de contenedor"), "c1");
    await user.type(screen.getByLabelText("ID de ubicación de referencia"), "u0");
    await user.click(screen.getByRole("button", { name: "Sugerir" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No hay ubicaciones disponibles que cumplan las restricciones"
    );
  });

  it("auto-selects and locks the patio when the user has only one assigned", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "operador", patios: ["p2"] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    render(<SugerirUbicacionPage />);

    const select = await screen.findByLabelText("Patio");
    expect(select).toBeDisabled();
    expect(select).toHaveValue("p2");
  });
});
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/ubicaciones/sugerir/page.test.tsx
```
Esperado: FAIL — `getByLabelText("Patio")` no encuentra nada.

- [ ] **Step 3: Modificar `frontend/app/ubicaciones/sugerir/page.tsx`**

El import pasa de:

```tsx
import { AuthGuard } from "@/components/AuthGuard";
```

a:

```tsx
import { AuthGuard } from "@/components/AuthGuard";
import { PatioSelect } from "@/components/PatioSelect";
```

Y el bloque:

```tsx
        <label htmlFor="patio_id">ID de patio</label>
        <input id="patio_id" value={patioId} onChange={(e) => setPatioId(e.target.value)} required />
```

se reemplaza por:

```tsx
        <label htmlFor="patio_id">Patio</label>
        <PatioSelect id="patio_id" value={patioId} onChange={setPatioId} />
```

El resto del archivo no cambia.

- [ ] **Step 4: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/ubicaciones/sugerir/page.test.tsx
```
Esperado: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/app/ubicaciones/sugerir/page.tsx frontend/app/ubicaciones/sugerir/page.test.tsx
git commit -m "feat: auto-relleno de patio en sugerencia de ubicacion"
```

---

### Task 7: Frontend — página `/usuarios` + link en NavBar

**Files:**
- Create: `frontend/app/usuarios/page.tsx`
- Create: `frontend/app/usuarios/page.module.css`
- Test: `frontend/app/usuarios/page.test.tsx`
- Modify: `frontend/components/NavBar.tsx`
- Modify: `frontend/components/NavBar.test.tsx`

**Interfaces:**
- Consumes: `listUsuarios`, `createUsuario`, `type Usuario`, `type RolUsuario` (Task 2); `usePatiosDisponibles` (Task 3); `AuthGuard`, `useAuth`.

- [ ] **Step 1: Escribir test que falla — NavBar**

Agregar a `frontend/components/NavBar.test.tsx`, dentro del `describe("NavBar", ...)`:

```tsx
  it("shows the Usuarios link only for admin", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "operador", patios: [] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });
    const { rerender } = render(<NavBar />);
    expect(screen.queryByText("Usuarios")).not.toBeInTheDocument();

    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "admin", patios: [] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });
    rerender(<NavBar />);
    expect(screen.getByText("Usuarios")).toBeInTheDocument();
  });
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- components/NavBar.test.tsx
```
Esperado: FAIL — `screen.getByText("Usuarios")` no encuentra nada.

- [ ] **Step 3: Modificar `frontend/components/NavBar.tsx`**

El bloque:

```tsx
      <div className={styles.links}>
        <Link href="/patios">Patios</Link>
        <Link href="/contenedores">Contenedores</Link>
        <Link href="/movimientos">Movimientos</Link>
        <Link href="/ubicaciones/sugerir">Sugerir ubicación</Link>
      </div>
```

se reemplaza por:

```tsx
      <div className={styles.links}>
        <Link href="/patios">Patios</Link>
        <Link href="/contenedores">Contenedores</Link>
        <Link href="/movimientos">Movimientos</Link>
        <Link href="/ubicaciones/sugerir">Sugerir ubicación</Link>
        {user.rol === "admin" && <Link href="/usuarios">Usuarios</Link>}
      </div>
```

- [ ] **Step 4: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- components/NavBar.test.tsx
```
Esperado: PASS (3 tests)

- [ ] **Step 5: Escribir test que falla — página de usuarios**

`frontend/app/usuarios/page.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import UsuariosPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { listUsuarios, createUsuario, listPatios } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, listUsuarios: vi.fn(), createUsuario: vi.fn(), listPatios: vi.fn() };
});

function mockAuth(rol: string, patios: string[] = []) {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "1", rol, patios },
    token: "token",
    ready: true,
    setToken: vi.fn(),
    logout: vi.fn(),
  });
}

const PATIOS = [
  { id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true },
  { id: "p2", nombre: "Patio Sur", codigo: "PS", activo: true },
];

beforeEach(() => {
  vi.mocked(listUsuarios).mockReset();
  vi.mocked(createUsuario).mockReset();
  vi.mocked(listPatios).mockReset();
  vi.mocked(listPatios).mockResolvedValue(PATIOS);
});

describe("UsuariosPage", () => {
  it("shows a not-authorized message for non-admin roles", async () => {
    mockAuth("operador", ["p1"]);

    render(<UsuariosPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("No autorizado");
    expect(listUsuarios).not.toHaveBeenCalled();
  });

  it("lists the usuarios returned by the backend for admin", async () => {
    mockAuth("admin");
    vi.mocked(listUsuarios).mockResolvedValue([
      {
        id: "u1",
        nombre: "Juan Operador",
        email: "juan@patio.mx",
        tipo: "operador",
        activo: true,
        patios: [{ id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true }],
      },
    ]);

    render(<UsuariosPage />);

    expect(await screen.findByText(/Juan Operador/)).toBeInTheDocument();
  });

  it("lets an admin create a usuario and refreshes the list", async () => {
    mockAuth("admin");
    vi.mocked(listUsuarios)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        {
          id: "u2",
          nombre: "Ana Supervisora",
          email: "ana@patio.mx",
          tipo: "supervisor",
          activo: true,
          patios: [{ id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true }],
        },
      ]);
    vi.mocked(createUsuario).mockResolvedValue({
      id: "u2",
      nombre: "Ana Supervisora",
      email: "ana@patio.mx",
      tipo: "supervisor",
      activo: true,
      patios: [{ id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true }],
    });

    const user = userEvent.setup();
    render(<UsuariosPage />);

    await screen.findByRole("button", { name: "Crear usuario" });
    await user.type(screen.getByLabelText("Nombre"), "Ana Supervisora");
    await user.type(screen.getByLabelText("Correo"), "ana@patio.mx");
    await user.type(screen.getByLabelText("Contraseña"), "clave1234");
    await user.selectOptions(screen.getByLabelText("Rol"), "supervisor");
    await user.click(screen.getByLabelText("Patio Norte (PN)"));
    await user.click(screen.getByRole("button", { name: "Crear usuario" }));

    expect(createUsuario).toHaveBeenCalledWith("token", {
      nombre: "Ana Supervisora",
      email: "ana@patio.mx",
      password: "clave1234",
      tipo: "supervisor",
      patio_ids: ["p1"],
    });
    expect(await screen.findByText(/Ana Supervisora/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 6: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/usuarios/page.test.tsx
```
Esperado: FAIL — `Cannot find module './page'`

- [ ] **Step 7: `frontend/app/usuarios/page.module.css`**

```css
.main {
  max-width: 720px;
  margin: 32px auto;
  padding: 0 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.list li {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 14px;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}

.form input,
.form select {
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
}

.form fieldset {
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form button {
  align-self: flex-start;
  background: var(--azul);
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
}

.error {
  color: var(--danger);
  background: var(--danger-soft);
  padding: 8px 10px;
  border-radius: 6px;
}
```

- [ ] **Step 8: `frontend/app/usuarios/page.tsx`**

```tsx
"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import { ApiError, createUsuario, listUsuarios, type RolUsuario, type Usuario } from "@/lib/api";
import { usePatiosDisponibles } from "@/lib/use-patios-disponibles";
import styles from "./page.module.css";

const ROLES: RolUsuario[] = ["operador", "supervisor", "guardia", "despachador", "admin"];

function UsuariosContent() {
  const { token, user } = useAuth();
  const { patios: patiosDisponibles } = usePatiosDisponibles();
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tipo, setTipo] = useState<RolUsuario>("operador");
  const [patioIds, setPatioIds] = useState<string[]>([]);
  const [creating, setCreating] = useState(false);

  const cargarUsuarios = useCallback(async () => {
    if (!token || user?.rol !== "admin") return;
    setLoading(true);
    try {
      const data = await listUsuarios(token);
      setUsuarios(data);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar los usuarios");
    } finally {
      setLoading(false);
    }
  }, [token, user]);

  useEffect(() => {
    cargarUsuarios();
  }, [cargarUsuarios]);

  function togglePatio(id: string) {
    setPatioIds((prev) => (prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]));
  }

  async function handleCrear(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setCreating(true);
    setError(null);
    try {
      await createUsuario(token, { nombre, email, password, tipo, patio_ids: patioIds });
      setNombre("");
      setEmail("");
      setPassword("");
      setTipo("operador");
      setPatioIds([]);
      await cargarUsuarios();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el usuario");
    } finally {
      setCreating(false);
    }
  }

  if (user?.rol !== "admin") {
    return (
      <main className={styles.main}>
        <p role="alert" className={styles.error}>
          No autorizado para ver esta página
        </p>
      </main>
    );
  }

  return (
    <main className={styles.main}>
      <h1>Usuarios</h1>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      {loading ? (
        <p>Cargando...</p>
      ) : (
        <ul className={styles.list}>
          {usuarios.map((u) => (
            <li key={u.id}>
              <strong>{u.nombre}</strong> — {u.email} — <span className="mono">{u.tipo}</span> —{" "}
              {u.patios.map((p) => p.codigo).join(", ") || "sin patios"}
            </li>
          ))}
        </ul>
      )}

      <form className={styles.form} onSubmit={handleCrear}>
        <h2>Nuevo usuario</h2>
        <label htmlFor="nombre">Nombre</label>
        <input id="nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required />

        <label htmlFor="email">Correo</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <label htmlFor="password">Contraseña</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
        />

        <label htmlFor="tipo">Rol</label>
        <select id="tipo" value={tipo} onChange={(e) => setTipo(e.target.value as RolUsuario)}>
          {ROLES.map((rol) => (
            <option key={rol} value={rol}>
              {rol}
            </option>
          ))}
        </select>

        <fieldset>
          <legend>Patios asignados</legend>
          {patiosDisponibles.map((patio) => (
            <label key={patio.id}>
              <input
                type="checkbox"
                checked={patioIds.includes(patio.id)}
                onChange={() => togglePatio(patio.id)}
              />
              {patio.nombre} ({patio.codigo})
            </label>
          ))}
        </fieldset>

        <button type="submit" disabled={creating}>
          {creating ? "Creando..." : "Crear usuario"}
        </button>
      </form>
    </main>
  );
}

export default function UsuariosPage() {
  return (
    <AuthGuard>
      <UsuariosContent />
    </AuthGuard>
  );
}
```

- [ ] **Step 9: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/usuarios/page.test.tsx
```
Esperado: PASS (3 tests)

- [ ] **Step 10: Correr toda la suite de frontend**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test
```
Esperado: PASS — todos los tests hasta este punto.

- [ ] **Step 11: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/app/usuarios frontend/components/NavBar.tsx frontend/components/NavBar.test.tsx
git commit -m "feat: pagina de usuarios (alta + listado, solo admin) y link en NavBar"
```

---

## Self-Review

**Cobertura del spec** (`docs/superpowers/specs/2026-09-18-gestion-usuarios-design.md`):
- Alta + listado de usuarios → Task 1 (backend) + Task 7 (frontend).
- Roles internos asignables (excluye `cliente`) → validado en Task 1 (`422` si `tipo == cliente`), reflejado en `ROLES` de Task 7.
- Uno o más patios por usuario → `patio_ids: list[uuid.UUID]` (Task 1), checkboxes múltiples (Task 7).
- Email duplicado → 409 → Task 1, test `test_email_duplicado_devuelve_409`.
- `patio_ids` requerido si rol no-admin → 422 → Task 1, test `test_rol_no_admin_sin_patios_devuelve_422`.
- Auto-relleno de patio en Contenedores/Sugerir ubicación, admin ve todos, resto solo los suyos, auto-select+disable si hay uno solo → Tasks 3, 4, 5, 6.
- `Movimientos` sin cambios (no tiene `patio_id`) → confirmado, ninguna task lo toca.
- Fuera de alcance (editar/desactivar usuarios, listar contenedores/ubicaciones por patio, rol cliente) → ninguna task lo implementa.

**Placeholder scan:** sin "TBD"/"similar a Task N"/pasos sin código — cada step tiene el archivo completo.

**Consistencia de tipos:** `Usuario`, `RolUsuario`, `PatiosDisponibles` y sus campos coinciden exactamente entre `lib/api.ts` (Task 2), `use-patios-disponibles.ts` (Task 3) y `PatioSelect.tsx` (Task 4). `UsuarioOut`/`UsuarioCreate` (backend, Task 1) coinciden campo a campo con `Usuario`/el payload de `createUsuario` (frontend, Task 2). `PatioSelect` se consume con la misma firma (`id`, `value`, `onChange`) en Tasks 5 y 6.
