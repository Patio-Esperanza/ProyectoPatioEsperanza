# Configurar layout de patio desde el UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an admin create/extend a patio's layout (carriles, tramos, tiras, niveles) from `/patios`, instead of requiring someone to run `seed_patio_layout.py` by hand.

**Architecture:** Extract the uniform-seeding logic already in `seed_patio_layout.py` into a shared service (`app/services/patio_layout.py`). A new `POST /api/patios/{patio_id}/layout` endpoint (admin only) calls that service and returns counts. The script is refactored to call the same service so both paths share one idempotency rule. `/patios` gets an admin-only "Layout" column: click opens an inline form (carriles/tramos/tiras/niveles) in that row, submit calls the new endpoint and shows the result.

**Tech Stack:** FastAPI + SQLAlchemy async (backend), Next.js + React + vitest/testing-library (frontend), pytest + pytest-asyncio + httpx (backend tests).

## Global Constraints

- Backend commands run from `/home/tony/Developer/ProyectoPatioEsperanza/backend` with `source .venv/bin/activate && PYTHONPATH=.` before `pytest`.
- Frontend commands run from `/home/tony/Developer/ProyectoPatioEsperanza/frontend`.
- `niveles` must stay within 1..5 (matches `ck_ubicacion_nivel_1_5` on `ubicaciones`).
- Only role `admin` may call the new endpoint (matches `crear_patio`/`actualizar_patio`).
- No schema/migration changes — this plan only adds rows through existing tables.
- No comments explaining WHAT code does; only WHY, and only when non-obvious (project style).
- Commit messages end with `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.

---

### Task 1: Extract layout-seeding into a shared service

**Files:**
- Create: `backend/app/services/patio_layout.py`
- Test: `backend/tests/test_patio_layout_service.py`

**Interfaces:**
- Produces: `async def sembrar_layout_uniforme(db: AsyncSession, patio: Patio, carriles: int, tramos: int, tiras: int, niveles: int) -> tuple[int, int, int]` returning `(carriles_creados, carriles_saltados, ubicaciones_creadas)`. Does not commit; caller commits.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_patio_layout_service.py`:

```python
import pytest
from sqlalchemy import select

from app.models.ubicacion import Carril, Patio, Ubicacion
from app.services.patio_layout import sembrar_layout_uniforme


async def _crear_patio(db_session, codigo: str) -> Patio:
    patio = Patio(nombre=f"Patio {codigo}", codigo=codigo)
    db_session.add(patio)
    await db_session.flush()
    return patio


@pytest.mark.anyio
async def test_sembrar_layout_uniforme_crea_la_jerarquia_completa(db_session):
    patio = await _crear_patio(db_session, "SL1")

    carriles_creados, carriles_saltados, ubicaciones_creadas = await sembrar_layout_uniforme(
        db_session, patio, carriles=2, tramos=1, tiras=1, niveles=3
    )
    await db_session.commit()

    assert carriles_creados == 2
    assert carriles_saltados == 0
    assert ubicaciones_creadas == 6

    codigos = await db_session.execute(select(Ubicacion.codigo))
    assert sorted(row[0] for row in codigos.all()) == [
        "A01-T01-R01-N1",
        "A01-T01-R01-N2",
        "A01-T01-R01-N3",
        "A02-T01-R01-N1",
        "A02-T01-R01-N2",
        "A02-T01-R01-N3",
    ]


@pytest.mark.anyio
async def test_sembrar_layout_uniforme_es_idempotente_por_carril(db_session):
    patio = await _crear_patio(db_session, "SL2")
    await sembrar_layout_uniforme(db_session, patio, carriles=2, tramos=1, tiras=1, niveles=2)
    await db_session.commit()

    carriles_creados, carriles_saltados, ubicaciones_creadas = await sembrar_layout_uniforme(
        db_session, patio, carriles=2, tramos=1, tiras=1, niveles=2
    )
    await db_session.commit()

    assert carriles_creados == 0
    assert carriles_saltados == 2
    assert ubicaciones_creadas == 0


@pytest.mark.anyio
async def test_sembrar_layout_uniforme_agrega_solo_los_carriles_nuevos(db_session):
    patio = await _crear_patio(db_session, "SL3")
    await sembrar_layout_uniforme(db_session, patio, carriles=1, tramos=1, tiras=1, niveles=2)
    await db_session.commit()

    carriles_creados, carriles_saltados, ubicaciones_creadas = await sembrar_layout_uniforme(
        db_session, patio, carriles=3, tramos=1, tiras=1, niveles=2
    )
    await db_session.commit()

    assert carriles_creados == 2
    assert carriles_saltados == 1
    assert ubicaciones_creadas == 4

    total_carriles = await db_session.execute(select(Carril).where(Carril.patio_id == patio.id))
    assert len(total_carriles.scalars().all()) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate && PYTHONPATH=. pytest tests/test_patio_layout_service.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.patio_layout'`

- [ ] **Step 3: Write the implementation**

Create `backend/app/services/patio_layout.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion


async def sembrar_layout_uniforme(
    db: AsyncSession,
    patio: Patio,
    carriles: int,
    tramos: int,
    tiras: int,
    niveles: int,
) -> tuple[int, int, int]:
    """Crea carriles/tramos/tiras/ubicaciones con codigos A01/T01/R01/N1.

    Salta por completo un carril cuyo codigo ya exista (no le agrega tramos
    nuevos). No hace commit: quien llama decide cuando.
    """
    carriles_creados = 0
    carriles_saltados = 0
    ubicaciones_creadas = 0

    for c in range(carriles):
        carril_codigo = f"A{c + 1:02d}"
        existente = await db.execute(
            select(Carril).where(Carril.patio_id == patio.id, Carril.codigo == carril_codigo)
        )
        if existente.scalar_one_or_none() is not None:
            carriles_saltados += 1
            continue

        carril = Carril(patio_id=patio.id, codigo=carril_codigo, orden=c)
        db.add(carril)
        await db.flush()
        carriles_creados += 1

        for t in range(tramos):
            tramo = Tramo(carril_id=carril.id, codigo=f"T{t + 1:02d}", orden=t)
            db.add(tramo)
            await db.flush()

            for r in range(tiras):
                tira = Tira(tramo_id=tramo.id, codigo=f"R{r + 1:02d}", orden=r)
                db.add(tira)
                await db.flush()

                for n in range(1, niveles + 1):
                    db.add(
                        Ubicacion(
                            tira_id=tira.id,
                            nivel=n,
                            codigo=f"{carril.codigo}-{tramo.codigo}-{tira.codigo}-N{n}",
                            activo=True,
                        )
                    )
                    ubicaciones_creadas += 1

    return carriles_creados, carriles_saltados, ubicaciones_creadas
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate && PYTHONPATH=. pytest tests/test_patio_layout_service.py -v
```
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/services/patio_layout.py backend/tests/test_patio_layout_service.py
git commit -m "$(cat <<'EOF'
Extrae siembra de layout uniforme a servicio compartido

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Refactor `seed_patio_layout.py` to use the shared service

**Files:**
- Modify: `backend/scripts/seed_patio_layout.py:1-30` (imports), `:89-127` (delete `_sembrar_uniforme`), `:198-201` (call site in `main`)

**Interfaces:**
- Consumes: `sembrar_layout_uniforme` from Task 1 (`app.services.patio_layout`).

- [ ] **Step 1: Replace the import block**

In `backend/scripts/seed_patio_layout.py`, change:

```python
from app.config import settings
from app.models.enums import TipoContenedor
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion
```

to:

```python
from app.config import settings
from app.models.enums import TipoContenedor
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion
from app.services.patio_layout import sembrar_layout_uniforme
```

- [ ] **Step 2: Delete `_sembrar_uniforme`**

Delete the entire function (lines 89-127 in the current file, from `async def _sembrar_uniforme(...)` through its `return creados, saltados`), including the blank lines directly above and below it that separate it from `_sembrar_config`.

- [ ] **Step 3: Update the call site in `main()`**

Change:

```python
        if carriles_config is not None:
            creados, saltados = await _sembrar_config(db, patio, carriles_config)
        else:
            creados, saltados = await _sembrar_uniforme(db, patio, args)

        await db.commit()
        print(f"Ubicaciones creadas: {creados}. Carriles saltados por ya existir: {saltados}.")
```

to:

```python
        if carriles_config is not None:
            creados, saltados = await _sembrar_config(db, patio, carriles_config)
        else:
            _carriles_creados, saltados, creados = await sembrar_layout_uniforme(
                db, patio, args.carriles, args.tramos, args.tiras, args.niveles
            )

        await db.commit()
        print(f"Ubicaciones creadas: {creados}. Carriles saltados por ya existir: {saltados}.")
```

- [ ] **Step 4: Verify the script still imports and parses args correctly**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate && PYTHONPATH=. python -m py_compile scripts/seed_patio_layout.py
source .venv/bin/activate && PYTHONPATH=. python -m scripts.seed_patio_layout --help
```
Expected: compiles with no output, and `--help` prints the same usage text as before (still shows `--patio-codigo`, `--config`, `--carriles`, `--tramos`, `--tiras`, `--niveles`, `--entrada`).

- [ ] **Step 5: Run the full backend test suite**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate && PYTHONPATH=. pytest -q
```
Expected: all tests pass (no test imports `_sembrar_uniforme` directly, so nothing else should break).

- [ ] **Step 6: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/scripts/seed_patio_layout.py
git commit -m "$(cat <<'EOF'
Usa el servicio compartido en seed_patio_layout --uniforme

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `POST /api/patios/{patio_id}/layout` endpoint

**Files:**
- Modify: `backend/app/schemas/patio.py:25` (end of file, add schemas)
- Modify: `backend/app/api/routes/patios.py:1-16` (imports), `:107` (end of file, add route)
- Test: `backend/tests/test_patios_api.py` (append)

**Interfaces:**
- Consumes: `sembrar_layout_uniforme` from Task 1.
- Produces: schemas `LayoutPatioCreate` (`carriles`, `tramos`, `tiras`, `niveles`, all `int`) and `LayoutPatioOut` (`carriles_creados`, `carriles_saltados`, `ubicaciones_creadas`, all `int`) in `app.schemas.patio`. Route `POST /api/patios/{patio_id}/layout`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_patios_api.py`:

```python
@pytest.mark.anyio
async def test_admin_configura_layout_de_patio(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    creado = await client.post(
        "/api/patios", json={"nombre": "Patio Layout", "codigo": "PL1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    patio_id = creado.json()["id"]

    response = await client.post(
        f"/api/patios/{patio_id}/layout",
        json={"carriles": 2, "tramos": 1, "tiras": 1, "niveles": 3},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {"carriles_creados": 2, "carriles_saltados": 0, "ubicaciones_creadas": 6}


@pytest.mark.anyio
async def test_configurar_layout_es_idempotente_por_carril(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    creado = await client.post(
        "/api/patios", json={"nombre": "Patio Layout 2", "codigo": "PL2"},
        headers={"Authorization": f"Bearer {token}"},
    )
    patio_id = creado.json()["id"]
    payload = {"carriles": 2, "tramos": 1, "tiras": 1, "niveles": 2}
    await client.post(
        f"/api/patios/{patio_id}/layout", json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    response = await client.post(
        f"/api/patios/{patio_id}/layout", json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "carriles_creados": 0,
        "carriles_saltados": 2,
        "ubicaciones_creadas": 0,
    }


@pytest.mark.anyio
async def test_operador_no_puede_configurar_layout(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    admin_token = _token(RolUsuario.ADMIN)
    creado = await client.post(
        "/api/patios", json={"nombre": "Patio Layout 3", "codigo": "PL3"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    patio_id = creado.json()["id"]

    op_token = _token(RolUsuario.OPERADOR)
    response = await client.post(
        f"/api/patios/{patio_id}/layout",
        json={"carriles": 1, "tramos": 1, "tiras": 1, "niveles": 1},
        headers={"Authorization": f"Bearer {op_token}"},
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_configurar_layout_patio_inexistente_404(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)

    response = await client.post(
        "/api/patios/00000000-0000-0000-0000-0000000000ff/layout",
        json={"carriles": 1, "tramos": 1, "tiras": 1, "niveles": 1},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_configurar_layout_niveles_fuera_de_rango_422(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    creado = await client.post(
        "/api/patios", json={"nombre": "Patio Layout 4", "codigo": "PL4"},
        headers={"Authorization": f"Bearer {token}"},
    )
    patio_id = creado.json()["id"]

    response = await client.post(
        f"/api/patios/{patio_id}/layout",
        json={"carriles": 1, "tramos": 1, "tiras": 1, "niveles": 6},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate && PYTHONPATH=. pytest tests/test_patios_api.py -k configura_layout -v
```
Expected: FAIL with 404 (route does not exist yet) on every new test.

- [ ] **Step 3: Add the schemas**

Append to `backend/app/schemas/patio.py`:

```python


class LayoutPatioCreate(BaseModel):
    carriles: int = Field(gt=0)
    tramos: int = Field(gt=0)
    tiras: int = Field(gt=0)
    niveles: int = Field(ge=1, le=5)


class LayoutPatioOut(BaseModel):
    carriles_creados: int
    carriles_saltados: int
    ubicaciones_creadas: int
```

- [ ] **Step 4: Add the route**

In `backend/app/api/routes/patios.py`, change the import block:

```python
from app.schemas.patio import PatioCreate, PatioOut, PatioUpdate
from app.services.mapa_patio import obtener_mapa
```

to:

```python
from app.schemas.patio import LayoutPatioCreate, LayoutPatioOut, PatioCreate, PatioOut, PatioUpdate
from app.services.mapa_patio import obtener_mapa
from app.services.patio_layout import sembrar_layout_uniforme
```

Append at the end of the file, after `mapa_patio`:

```python


@router.post("/{patio_id}/layout", response_model=LayoutPatioOut)
async def configurar_layout_patio(
    patio_id: uuid.UUID,
    payload: LayoutPatioCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.ADMIN)),
) -> LayoutPatioOut:
    result = await db.execute(select(Patio).where(Patio.id == patio_id))
    patio = result.scalar_one_or_none()
    if patio is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patio no encontrado")

    carriles_creados, carriles_saltados, ubicaciones_creadas = await sembrar_layout_uniforme(
        db, patio, payload.carriles, payload.tramos, payload.tiras, payload.niveles
    )

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="configurar_layout",
        entidad="patios",
        entidad_id=str(patio.id),
        valor_anterior=None,
        valor_nuevo={
            "carriles_creados": carriles_creados,
            "carriles_saltados": carriles_saltados,
            "ubicaciones_creadas": ubicaciones_creadas,
        },
        patio_id=patio.id,
    )
    await db.commit()
    return LayoutPatioOut(
        carriles_creados=carriles_creados,
        carriles_saltados=carriles_saltados,
        ubicaciones_creadas=ubicaciones_creadas,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate && PYTHONPATH=. pytest tests/test_patios_api.py -v
```
Expected: all tests in the file pass, including the 5 new ones.

- [ ] **Step 6: Run the full backend suite**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate && PYTHONPATH=. pytest -q
```
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/schemas/patio.py backend/app/api/routes/patios.py backend/tests/test_patios_api.py
git commit -m "$(cat <<'EOF'
Agrega POST /api/patios/{id}/layout para sembrar layout uniforme

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Frontend API client for the layout endpoint

**Files:**
- Modify: `frontend/lib/api.ts:99-110` (after `createPatio`, before the `TipoContenedor` type block)
- Modify: `frontend/lib/api.test.ts:451` (after the `actualizarPatio` describe block, before `obtenerMapaPatio`)

**Interfaces:**
- Produces: `interface LayoutPatioPayload { carriles: number; tramos: number; tiras: number; niveles: number }`, `interface LayoutPatioResultado { carriles_creados: number; carriles_saltados: number; ubicaciones_creadas: number }`, `async function configurarLayoutPatio(token: string, patioId: string, payload: LayoutPatioPayload): Promise<LayoutPatioResultado>` in `frontend/lib/api.ts`.

- [ ] **Step 1: Write the failing test**

In `frontend/lib/api.test.ts`, add `configurarLayoutPatio` to the import list (after `actualizarPatio,` on line 29):

```typescript
  actualizarPatio,
  configurarLayoutPatio,
} from "./api";
```

Insert this `describe` block right after the `actualizarPatio` describe block (after its closing `});` at line 451, before `describe("obtenerMapaPatio", ...)`):

```typescript
describe("configurarLayoutPatio", () => {
  it("posts the layout payload and returns the counts", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ carriles_creados: 2, carriles_saltados: 0, ubicaciones_creadas: 6 })
    );

    const resultado = await configurarLayoutPatio("token", "p1", {
      carriles: 2,
      tramos: 1,
      tiras: 1,
      niveles: 3,
    });

    expect(resultado).toEqual({ carriles_creados: 2, carriles_saltados: 0, ubicaciones_creadas: 6 });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/patios/p1/layout",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ carriles: 2, tramos: 1, tiras: 1, niveles: 3 }),
        headers: expect.objectContaining({ Authorization: "Bearer token" }),
      })
    );
  });

  it("throws ApiError with the backend detail on failure", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 422,
      statusText: "Unprocessable Entity",
      json: async () => ({ detail: "niveles debe estar entre 1 y 5" }),
    });

    await expect(
      configurarLayoutPatio("token", "p1", { carriles: 1, tramos: 1, tiras: 1, niveles: 9 })
    ).rejects.toThrow("niveles debe estar entre 1 y 5");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
NODE_ENV=test npx vitest run lib/api.test.ts
```
Expected: FAIL — `configurarLayoutPatio` is not exported from `./api`.

- [ ] **Step 3: Implement `configurarLayoutPatio`**

In `frontend/lib/api.ts`, after `createPatio` (ends line 110, right before `export type TipoContenedor = "lleno" | "vacio";`), insert:

```typescript
export interface LayoutPatioPayload {
  carriles: number;
  tramos: number;
  tiras: number;
  niveles: number;
}

export interface LayoutPatioResultado {
  carriles_creados: number;
  carriles_saltados: number;
  ubicaciones_creadas: number;
}

export async function configurarLayoutPatio(
  token: string,
  patioId: string,
  payload: LayoutPatioPayload
): Promise<LayoutPatioResultado> {
  return request<LayoutPatioResultado>(`/api/patios/${patioId}/layout`, {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
NODE_ENV=test npx vitest run lib/api.test.ts
```
Expected: all tests in the file pass.

- [ ] **Step 5: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/lib/api.ts frontend/lib/api.test.ts
git commit -m "$(cat <<'EOF'
Agrega configurarLayoutPatio al cliente de API

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: "Configurar layout" en `/patios`

**Files:**
- Modify: `frontend/app/patios/page.tsx`
- Modify: `frontend/app/patios/page.module.css`
- Modify: `frontend/app/patios/page.test.tsx`

**Interfaces:**
- Consumes: `configurarLayoutPatio`, `LayoutPatioPayload`, `LayoutPatioResultado` from Task 4.

- [ ] **Step 1: Write the failing tests**

In `frontend/app/patios/page.test.tsx`, replace:

```typescript
import { listPatios, createPatio, actualizarPatio } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, listPatios: vi.fn(), createPatio: vi.fn(), actualizarPatio: vi.fn() };
});
```

with:

```typescript
import { ApiError, listPatios, createPatio, actualizarPatio, configurarLayoutPatio } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    listPatios: vi.fn(),
    createPatio: vi.fn(),
    actualizarPatio: vi.fn(),
    configurarLayoutPatio: vi.fn(),
  };
});
```

Replace:

```typescript
beforeEach(() => {
  vi.mocked(listPatios).mockReset();
  vi.mocked(createPatio).mockReset();
  vi.mocked(actualizarPatio).mockReset();
});
```

with:

```typescript
beforeEach(() => {
  vi.mocked(listPatios).mockReset();
  vi.mocked(createPatio).mockReset();
  vi.mocked(actualizarPatio).mockReset();
  vi.mocked(configurarLayoutPatio).mockReset();
});
```

Add these tests at the end of the `describe("PatiosPage", ...)` block, right before its closing `});`:

```typescript
  it("hides the 'Configurar layout' button for non-admin roles", async () => {
    mockAuth("operador");
    vi.mocked(listPatios).mockResolvedValue([
      { id: "1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 },
    ]);

    render(<PatiosPage />);

    await screen.findByText(/Patio Norte/);
    expect(screen.queryByRole("button", { name: "Configurar layout" })).not.toBeInTheDocument();
  });

  it("lets an admin configure a patio's layout and shows the result", async () => {
    mockAuth("admin");
    vi.mocked(listPatios).mockResolvedValue([
      { id: "1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 },
    ]);
    vi.mocked(configurarLayoutPatio).mockResolvedValue({
      carriles_creados: 2,
      carriles_saltados: 0,
      ubicaciones_creadas: 6,
    });

    const user = userEvent.setup();
    render(<PatiosPage />);

    await user.click(await screen.findByRole("button", { name: "Configurar layout" }));
    await user.type(screen.getByLabelText("Carriles"), "2");
    await user.type(screen.getByLabelText("Tramos"), "1");
    await user.type(screen.getByLabelText("Tiras"), "1");
    await user.type(screen.getByLabelText("Niveles"), "3");
    await user.click(screen.getByRole("button", { name: "Aplicar" }));

    expect(configurarLayoutPatio).toHaveBeenCalledWith("token", "1", {
      carriles: 2,
      tramos: 1,
      tiras: 1,
      niveles: 3,
    });
    expect(await screen.findByText(/Se crearon 6 ubicaciones/)).toBeInTheDocument();
  });

  it("shows an error when configuring the layout fails", async () => {
    mockAuth("admin");
    vi.mocked(listPatios).mockResolvedValue([
      { id: "1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 },
    ]);
    vi.mocked(configurarLayoutPatio).mockRejectedValue(new ApiError(422, "niveles invalido"));

    const user = userEvent.setup();
    render(<PatiosPage />);

    await user.click(await screen.findByRole("button", { name: "Configurar layout" }));
    await user.type(screen.getByLabelText("Carriles"), "2");
    await user.type(screen.getByLabelText("Tramos"), "1");
    await user.type(screen.getByLabelText("Tiras"), "1");
    await user.type(screen.getByLabelText("Niveles"), "3");
    await user.click(screen.getByRole("button", { name: "Aplicar" }));

    expect(await screen.findByText("niveles invalido")).toBeInTheDocument();
  });

  it("does not submit the layout form when a field is left empty", async () => {
    mockAuth("admin");
    vi.mocked(listPatios).mockResolvedValue([
      { id: "1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 },
    ]);

    const user = userEvent.setup();
    render(<PatiosPage />);

    await user.click(await screen.findByRole("button", { name: "Configurar layout" }));
    await user.type(screen.getByLabelText("Carriles"), "2");
    await user.click(screen.getByRole("button", { name: "Aplicar" }));

    expect(configurarLayoutPatio).not.toHaveBeenCalled();
  });

  it("does not submit the layout form when niveles is out of the 1..5 range", async () => {
    mockAuth("admin");
    vi.mocked(listPatios).mockResolvedValue([
      { id: "1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 },
    ]);

    const user = userEvent.setup();
    render(<PatiosPage />);

    await user.click(await screen.findByRole("button", { name: "Configurar layout" }));
    await user.type(screen.getByLabelText("Carriles"), "2");
    await user.type(screen.getByLabelText("Tramos"), "1");
    await user.type(screen.getByLabelText("Tiras"), "1");
    await user.type(screen.getByLabelText("Niveles"), "6");
    await user.click(screen.getByRole("button", { name: "Aplicar" }));

    expect(configurarLayoutPatio).not.toHaveBeenCalled();
  });
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
NODE_ENV=test npx vitest run app/patios/page.test.tsx
```
Expected: FAIL — no button named "Configurar layout" exists yet.

- [ ] **Step 3: Add the CSS classes**

Append to `frontend/app/patios/page.module.css`:

```css

.celdaLayout {
  display: flex;
  justify-content: flex-end;
}

.formularioLayout {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 220px;
}

.camposLayout {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-2);
}

.campoLayout {
  max-width: 100px;
}

.accionesLayout {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
```

- [ ] **Step 4: Implement the column, state and handlers in `page.tsx`**

Change the imports at the top of `frontend/app/patios/page.tsx`. Replace:

```typescript
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { ROLES_POR_RUTA } from "@/lib/rutas";
import { useAuth } from "@/lib/auth-context";
import { ApiError, actualizarPatio, createPatio, listPatios, type Patio } from "@/lib/api";
```

with:

```typescript
import { useCallback, useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { ROLES_POR_RUTA } from "@/lib/rutas";
import { useAuth } from "@/lib/auth-context";
import {
  ApiError,
  actualizarPatio,
  configurarLayoutPatio,
  createPatio,
  listPatios,
  type LayoutPatioResultado,
  type Patio,
} from "@/lib/api";
```

Inside `PatiosContent`, right after the existing state declarations (after `const [creating, setCreating] = useState(false);`), add:

```typescript
  const [layoutAbierto, setLayoutAbierto] = useState<string | null>(null);
  const [layoutValores, setLayoutValores] = useState({
    carriles: "",
    tramos: "",
    tiras: "",
    niveles: "",
  });
  const [layoutEnviando, setLayoutEnviando] = useState(false);
  const [layoutResultado, setLayoutResultado] = useState<LayoutPatioResultado | null>(null);
  const [layoutErrorLocal, setLayoutErrorLocal] = useState<string | null>(null);
```

Right after `handleActualizarAnticipacion` (before `const columnas = [...]`), add:

```typescript
  function abrirLayout(patioId: string) {
    setLayoutAbierto(patioId);
    setLayoutValores({ carriles: "", tramos: "", tiras: "", niveles: "" });
    setLayoutResultado(null);
    setLayoutErrorLocal(null);
  }

  function cerrarLayout() {
    setLayoutAbierto(null);
  }

  function actualizarCampoLayout(campo: keyof typeof layoutValores) {
    return (event: ChangeEvent<HTMLInputElement>) => {
      const valor = event.target.value;
      setLayoutValores((previo) => ({ ...previo, [campo]: valor }));
    };
  }

  function layoutValoresSonValidos() {
    const { carriles, tramos, tiras, niveles } = layoutValores;
    const numeros = [carriles, tramos, tiras, niveles].map(Number);
    if (numeros.some((n) => Number.isNaN(n))) return false;
    const [nCarriles, nTramos, nTiras, nNiveles] = numeros;
    return nCarriles >= 1 && nTramos >= 1 && nTiras >= 1 && nNiveles >= 1 && nNiveles <= 5;
  }

  async function handleConfigurarLayout(event: FormEvent<HTMLFormElement>, patioId: string) {
    event.preventDefault();
    if (!token || !layoutValoresSonValidos()) return;

    setLayoutEnviando(true);
    setLayoutErrorLocal(null);
    try {
      const resultado = await configurarLayoutPatio(token, patioId, {
        carriles: Number(layoutValores.carriles),
        tramos: Number(layoutValores.tramos),
        tiras: Number(layoutValores.tiras),
        niveles: Number(layoutValores.niveles),
      });
      setLayoutResultado(resultado);
    } catch (err) {
      setLayoutErrorLocal(err instanceof ApiError ? err.message : "No se pudo configurar el layout");
    } finally {
      setLayoutEnviando(false);
    }
  }
```

Change the `columnas` definition. Replace:

```typescript
  const columnas = [
    { key: "codigo", header: "Código", mono: true },
    { key: "nombre", header: "Nombre" },
    ...(esAdmin
      ? [{ key: "anticipacion", header: "Anticipación mínima (h)", align: "end" as const }]
      : []),
  ];
```

with:

```typescript
  const columnas = [
    { key: "codigo", header: "Código", mono: true },
    { key: "nombre", header: "Nombre" },
    ...(esAdmin
      ? [
          { key: "anticipacion", header: "Anticipación mínima (h)", align: "end" as const },
          { key: "layout", header: "Layout", align: "end" as const },
        ]
      : []),
  ];
```

In `renderCelda`, add the `layout` case right before the final `return` (the one that renders the `anticipacion` field):

```typescript
  function renderCelda(patio: Patio, key: string) {
    if (key === "codigo") return patio.codigo;
    if (key === "nombre") return patio.nombre;
    if (key === "layout") {
      if (layoutAbierto !== patio.id) {
        return (
          <span className={styles.celdaLayout}>
            <Button variant="secondary" size="sm" onClick={() => abrirLayout(patio.id)}>
              Configurar layout
            </Button>
          </span>
        );
      }
      return (
        <div className={styles.celdaLayout}>
          <form
            className={styles.formularioLayout}
            onSubmit={(e) => handleConfigurarLayout(e, patio.id)}
          >
            <div className={styles.camposLayout}>
              <Field
                label="Carriles"
                id={`layout-carriles-${patio.id}`}
                type="number"
                min={1}
                required
                className={styles.campoLayout}
                value={layoutValores.carriles}
                onChange={actualizarCampoLayout("carriles")}
              />
              <Field
                label="Tramos"
                id={`layout-tramos-${patio.id}`}
                type="number"
                min={1}
                required
                className={styles.campoLayout}
                value={layoutValores.tramos}
                onChange={actualizarCampoLayout("tramos")}
              />
              <Field
                label="Tiras"
                id={`layout-tiras-${patio.id}`}
                type="number"
                min={1}
                required
                className={styles.campoLayout}
                value={layoutValores.tiras}
                onChange={actualizarCampoLayout("tiras")}
              />
              <Field
                label="Niveles"
                id={`layout-niveles-${patio.id}`}
                type="number"
                min={1}
                max={5}
                required
                className={styles.campoLayout}
                value={layoutValores.niveles}
                onChange={actualizarCampoLayout("niveles")}
              />
            </div>
            {layoutResultado && (
              <Alert tone="success">
                Se crearon {layoutResultado.ubicaciones_creadas} ubicaciones en{" "}
                {layoutResultado.carriles_creados} carriles nuevos. {layoutResultado.carriles_saltados}{" "}
                carriles ya existían y se omitieron.
              </Alert>
            )}
            {layoutErrorLocal && <Alert tone="danger">{layoutErrorLocal}</Alert>}
            <div className={styles.accionesLayout}>
              <Button type="button" variant="ghost" size="sm" onClick={cerrarLayout}>
                Cerrar
              </Button>
              <Button type="submit" size="sm" loading={layoutEnviando}>
                Aplicar
              </Button>
            </div>
          </form>
        </div>
      );
    }
    return (
      // El envoltorio de Field es un bloque y llenaría la celda, dejando el campo pegado
      // a la izquierda aunque la columna esté alineada a la derecha.
      <span className={styles.celdaAnticipacion}>
        <Field
          // La etiqueta lleva el código del patio porque hay un campo por fila y, sin él,
          // un lector de pantalla oiría la misma etiqueta repetida en toda la tabla.
          label={`Anticipación mínima (h) — ${patio.codigo}`}
          // El encabezado de la columna ya muestra el nombre del campo: repetirlo en cada
          // fila sería ruido. Sigue anunciándose a los lectores de pantalla.
          labelHidden
          id={`anticipacion-${patio.id}`}
          type="number"
          min={1}
          defaultValue={patio.anticipacion_minima_horas}
          onBlur={(e) => handleActualizarAnticipacion(patio.id, Number(e.target.value))}
          className={styles.anticipacion}
        />
      </span>
    );
  }
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
NODE_ENV=test npx vitest run app/patios/page.test.tsx
```
Expected: all tests in the file pass, including the 5 new ones.

- [ ] **Step 6: Run the full frontend suite**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test
```
Expected: all tests pass.

- [ ] **Step 7: Manual check in the browser**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm run dev
```

Log in as admin, go to `/patios`, click "Configurar layout" on a row, fill in small numbers (e.g. 1/1/1/2), click "Aplicar", confirm the success message shows and no console errors appear. Click "Aplicar" again with the same values and confirm it reports the carril as skipped (`carriles_saltados: 1`).

- [ ] **Step 8: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/app/patios/page.tsx frontend/app/patios/page.module.css frontend/app/patios/page.test.tsx
git commit -m "$(cat <<'EOF'
Agrega formulario de configurar layout a la pantalla de patios

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Post-implementation check

- [ ] Run `cd backend && source .venv/bin/activate && PYTHONPATH=. pytest -q` — all green.
- [ ] Run `cd frontend && npm test` — all green.
- [ ] Update spec status in `docs/superpowers/specs/2026-09-29-configurar-layout-patio-ui-design.md` from "aprobado, pendiente de plan de implementación" to "implementado".
