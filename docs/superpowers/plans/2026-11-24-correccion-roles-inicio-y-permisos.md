# Corrección de compilación, inicio por rol y permisos. Plan de implementación

> Spec: `docs/superpowers/specs/2026-11-24-correccion-roles-inicio-y-permisos-design.md`
> Método: TDD task por task. Test que falla, implementación, test verde, commit.
> Commits en Conventional Commits, en español y sin acentos.

**Objetivo:** que el frontend compile, que cada rol aterrice en una pantalla que puede ver,
y que ninguna ruta muestre a un rol una página cuyo backend le responde 403.

**Rama sugerida:** `fix/roles-inicio-permisos` desde `master`.

---

## Task 1: Tipos de `PanelCuadrilla`

**Archivos**
- Modificar: `frontend/components/PanelCuadrilla.tsx`
- Modificar: `frontend/tests/servicios_cuadrilla.test.tsx`

- [ ] **Paso 1: prueba que falla.** Agregar al archivo de prueba:

```tsx
import { ApiError, listarServicios } from "@/lib/api";

test("shows the load error as an alert", async () => {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "1", rol: "cuadrilla", patios: [] },
    token: "token",
    ready: true,
    setToken: vi.fn(),
    logout: vi.fn(),
    tokenExpiresAt: null,
    proximaExpiracion: false,
    errorRefresh: false,
    renovarSesion: vi.fn(),
  });
  vi.mocked(listarServicios).mockRejectedValueOnce(new ApiError(500, "Fallo del servidor"));

  render(<ServiciosPage />);

  expect(await screen.findByRole("alert")).toHaveTextContent("Fallo del servidor");
});
```

- [ ] **Paso 2:** `cd frontend && npx vitest run tests/servicios_cuadrilla.test.tsx`. Debe fallar
  (sin `tone`, `Alert` usa `role="status"`).
- [ ] **Paso 3:** en `PanelCuadrilla.tsx`, cambiar `<Alert variant="error">` por
  `<Alert tone="danger">` y `<Button variant="outline"` por `<Button variant="secondary"`.
- [ ] **Paso 4:** correr la prueba y `npx tsc --noEmit`. Ambos limpios.
- [ ] **Paso 5:** commit.

```bash
git add frontend/components/PanelCuadrilla.tsx frontend/tests/servicios_cuadrilla.test.tsx
git commit -m "fix(servicios): corregir props de Alert y Button en PanelCuadrilla"
```

---

## Task 2: Mapa de rutas e inicio por rol

**Archivos**
- Modificar: `frontend/lib/rutas.ts`
- Modificar: `frontend/lib/rutas.test.ts`

- [ ] **Paso 1: pruebas que fallan.** Reemplazar el contenido de `rutas.test.ts` por:

```ts
import { describe, expect, it } from "vitest";
import { ROLES_POR_RUTA, ROLES_STAFF, homePorRol } from "./rutas";

/** Espejo de `RolUsuario` en `backend/app/models/enums.py`. */
const TODOS_LOS_ROLES = [
  "cliente",
  "operador",
  "supervisor",
  "admin",
  "guardia",
  "despachador",
  "operador_grua",
  "cuadrilla",
];

describe("homePorRol", () => {
  it.each([
    ["cliente", "/mis-contenedores"],
    ["cuadrilla", "/servicios"],
    ["guardia", "/porteria"],
    ["despachador", "/salidas"],
    ["operador", "/patios"],
    ["supervisor", "/patios"],
    ["admin", "/patios"],
    ["operador_grua", "/inicio"],
    ["desconocido", "/inicio"],
  ])("sends %s to %s", (rol, ruta) => {
    expect(homePorRol(rol)).toBe(ruta);
  });

  it.each(TODOS_LOS_ROLES)("lands %s on a route it can see", (rol) => {
    const permitidos = ROLES_POR_RUTA[homePorRol(rol)];
    expect(permitidos === undefined || permitidos.includes(rol)).toBe(true);
  });
});

describe("ROLES_POR_RUTA", () => {
  it("restricts the admin-only routes to admin", () => {
    expect(ROLES_POR_RUTA["/usuarios"]).toEqual(["admin"]);
    expect(ROLES_POR_RUTA["/clientes"]).toEqual(["admin"]);
  });

  it("restricts the cliente routes to cliente", () => {
    expect(ROLES_POR_RUTA["/solicitar"]).toEqual(["cliente"]);
    expect(ROLES_POR_RUTA["/mis-contenedores"]).toEqual(["cliente"]);
  });

  it("gives the plain staff routes the three writing roles of the backend", () => {
    for (const ruta of ["/patios", "/contenedores", "/movimientos", "/ubicaciones/sugerir", "/mapa"]) {
      expect(ROLES_POR_RUTA[ruta]).toEqual([...ROLES_STAFF]);
    }
  });

  it("matches the backend for the operational routes", () => {
    expect(ROLES_POR_RUTA["/porteria"]).toEqual(["guardia", ...ROLES_STAFF]);
    expect(ROLES_POR_RUTA["/salidas"]).toEqual(["despachador", ...ROLES_STAFF]);
    expect(ROLES_POR_RUTA["/servicios"]).toEqual(["cuadrilla", "supervisor", "admin"]);
  });

  it("never lets a cliente into a staff route", () => {
    for (const roles of Object.values(ROLES_POR_RUTA)) {
      if (roles.includes("operador") || roles.includes("supervisor")) {
        if (roles !== ROLES_POR_RUTA["/reportes"]) {
          expect(roles).not.toContain("cliente");
        }
      }
    }
  });
});
```

- [ ] **Paso 2:** `npx vitest run lib/rutas.test.ts`. Debe fallar.
- [ ] **Paso 3:** en `rutas.ts`:
  - `"/mapa": [...ROLES_STAFF]` con comentario: `_ROLES_MAPA` y `POST /api/movimientos`.
  - `"/porteria": ["guardia", ...ROLES_STAFF]` con comentario: `verificar-pin` acepta
    `_ROLES_ESCRITURA` y `guardia` (Task 3).
  - `"/salidas": ["despachador", ...ROLES_STAFF]` con comentario: `GET /api/contenedores`
    acepta cualquier sesión; RLS filtra por patio.
  - `"/servicios": ["cuadrilla", "supervisor", "admin"]` con comentario: `_ROLES_GESTION_ORDEN`
    de `backend/app/api/servicios.py`.
  - `homePorRol`:

```ts
const INICIO_POR_ROL: Record<string, string> = {
  cliente: "/mis-contenedores",
  cuadrilla: "/servicios",
  guardia: "/porteria",
  despachador: "/salidas",
  operador: "/patios",
  supervisor: "/patios",
  admin: "/patios",
};

/**
 * Ruta de inicio de cada rol. La usan el login, la raíz `/` y la pantalla de acceso
 * denegado. Un rol sin pantalla propia (hoy `operador_grua`) o desconocido va a `/inicio`,
 * que solo exige sesión, para no caer en un acceso denegado que regresa a otro.
 */
export function homePorRol(rol: string): string {
  return INICIO_POR_ROL[rol] ?? "/inicio";
}
```

- [ ] **Paso 4:** la prueba de rutas pasa. La invariante de `operador_grua` depende de que
  `/inicio` no tenga entrada en `ROLES_POR_RUTA`; no agregarla.
- [ ] **Paso 5:** correr `npx vitest run components/Sidebar.test.tsx`. Si alguna prueba
  asumía que operador ve "Servicios" o que operador_grua ve "Mapa", actualizarla al nuevo mapa.
- [ ] **Paso 6:** commit.

```bash
git add frontend/lib/rutas.ts frontend/lib/rutas.test.ts frontend/components/Sidebar.test.tsx
git commit -m "fix(rutas): alinear roles por ruta con el backend e inicio por rol"
```

---

## Task 3: `verificar-pin` acepta guardia

**Archivos**
- Modificar: `backend/app/api/routes/contenedores.py`
- Modificar: `backend/tests/test_contenedores_api.py`

- [ ] **Paso 1: pruebas que fallan.** Agregar después de `test_cliente_no_puede_verificar_pin`:

```python
@pytest.mark.anyio
async def test_guardia_verifica_pin_de_su_patio(client, db_session, enviados_pin):
    contenedor_id, _ = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-0000000000c1", "GUA111111GU1", "CSQU3054010"
    )
    result = await db_session.execute(select(Contenedor).where(Contenedor.id == contenedor_id))
    contenedor = result.scalar_one()
    await _crear_usuario_autenticado(db_session)
    token = _token(RolUsuario.GUARDIA, patios=[str(contenedor.patio_id)])

    response = await client.post(
        "/api/contenedores/verificar-pin",
        json={"numero_contenedor": "CSQU3054010", "pin": contenedor.pin_confirmacion},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["estado"] == "en_porteria"


@pytest.mark.anyio
async def test_guardia_sin_patios_no_verifica_pin(client, db_session, enviados_pin):
    await _crear_usuario_autenticado(db_session)
    token = _token(RolUsuario.GUARDIA)

    response = await client.post(
        "/api/contenedores/verificar-pin",
        json={"numero_contenedor": "CSQU3054010", "pin": "1234"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_guardia_de_otro_patio_recibe_404(client, db_session, enviados_pin):
    contenedor_id, _ = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-0000000000c2", "GUA222222GU2", "CSQU3054026"
    )
    result = await db_session.execute(select(Contenedor).where(Contenedor.id == contenedor_id))
    contenedor = result.scalar_one()
    await _crear_usuario_autenticado(db_session)
    token = _token(RolUsuario.GUARDIA, patios=[str(uuid.uuid4())])

    response = await client.post(
        "/api/contenedores/verificar-pin",
        json={"numero_contenedor": "CSQU3054026", "pin": contenedor.pin_confirmacion},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
```

  Antes de fijar los números de contenedor, confirmar que `CSQU3054010` y `CSQU3054026`
  pasan el dígito de control ISO 6346 con `app.core.iso6346`; si no, ajustar el último
  dígito al que calcule la función.

- [ ] **Paso 2:** `cd backend && pytest tests/test_contenedores_api.py -k guardia -v`. Debe fallar con 403.
- [ ] **Paso 3:** en `contenedores.py`:

```python
_ROLES_VERIFICAR_PIN = (*_ROLES_ESCRITURA, RolUsuario.GUARDIA)
```

  y en `verificar_pin`:

```python
    user: CurrentUser = Depends(require_roles(*_ROLES_VERIFICAR_PIN)),
) -> Contenedor:
    if user.rol == RolUsuario.GUARDIA and not user.patios:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Guardia sin patios asignados")

    query = select(Contenedor).where(Contenedor.numero_contenedor == payload.numero_contenedor)
    # Filtro explícito además de RLS: las políticas conservan el bypass IS NULL.
    if user.rol == RolUsuario.GUARDIA:
        query = query.where(Contenedor.patio_id.in_(user.patios))
    result = await db.execute(query)
```

- [ ] **Paso 4:** `pytest tests/test_contenedores_api.py -v`. Todo en verde, incluidas las
  pruebas previas de operador y cliente.
- [ ] **Paso 5:** commit.

```bash
git add backend/app/api/routes/contenedores.py backend/tests/test_contenedores_api.py
git commit -m "feat(porteria): permitir al guardia verificar el PIN de su patio"
```

---

## Task 4: Login y raíz usan `homePorRol`

**Archivos**
- Modificar: `frontend/app/login/page.tsx`, `frontend/app/login/page.test.tsx`
- Modificar: `frontend/app/page.tsx`, `frontend/app/page.test.tsx`

- [ ] **Paso 1: pruebas que fallan.**

  En `login/page.test.tsx`, agregar:

```tsx
it("sends a cuadrilla to Servicios after login", async () => {
  const user = userEvent.setup();
  const payload = { sub: "usr-2", rol: "cuadrilla", patios: [], iat: 0, exp: 9999999999 };
  const token = `${btoa("{}")}.${btoa(JSON.stringify(payload))}.sig`;
  vi.mocked(login).mockResolvedValue({ access_token: token, token_type: "bearer" });

  render(
    <AuthProvider>
      <LoginPage />
    </AuthProvider>
  );

  await user.type(screen.getByLabelText("Correo"), "cuadrilla@patio.mx");
  await user.type(screen.getByLabelText("Contraseña"), "clave123");
  await user.click(screen.getByRole("button", { name: "Entrar" }));

  await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/servicios"));
});

it("prefers the saved return route over the role home", async () => {
  const user = userEvent.setup();
  sessionStorage.setItem("patio_esperanza_ruta_retorno", "/contenedores");
  vi.mocked(login).mockResolvedValue({ access_token: FAKE_TOKEN, token_type: "bearer" });

  render(
    <AuthProvider>
      <LoginPage />
    </AuthProvider>
  );

  await user.type(screen.getByLabelText("Correo"), "admin@patio.mx");
  await user.type(screen.getByLabelText("Contraseña"), "clave123");
  await user.click(screen.getByRole("button", { name: "Entrar" }));

  await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/contenedores"));
});
```

  En `app/page.test.tsx`, agregar casos con `rol: "cliente"` esperando `/mis-contenedores`
  y `rol: "guardia"` esperando `/porteria`, con el mismo mock de `useAuth` que ya usa.

- [ ] **Paso 2:** correr ambas pruebas. Deben fallar.
- [ ] **Paso 3:** implementación.

  `login/page.tsx`:

```tsx
import { homePorRol } from "@/lib/rutas";
import { decodeTokenSafe } from "@/lib/jwt";
// ...
      const { access_token } = await login(email, password);
      setToken(access_token);
      // `user` del contexto aún no refleja el token nuevo en este manejador.
      const rol = decodeTokenSafe(access_token)?.rol ?? "";
      router.push(tomarRutaRetorno() ?? homePorRol(rol));
```

  `app/page.tsx`:

```tsx
import { homePorRol } from "@/lib/rutas";
// ...
    router.replace(user ? homePorRol(user.rol) : "/login");
```

- [ ] **Paso 4:** pruebas en verde. La prueba existente "logs in and redirects to /patios"
  sigue pasando porque el token falso es de `admin`.
- [ ] **Paso 5:** commit.

```bash
git add frontend/app/login frontend/app/page.tsx frontend/app/page.test.tsx
git commit -m "fix(auth): redirigir al inicio de cada rol despues del login"
```

---

## Task 5: Página `/inicio` para roles sin pantalla

**Archivos**
- Crear: `frontend/app/inicio/page.tsx`, `frontend/app/inicio/page.module.css`,
  `frontend/app/inicio/page.test.tsx`

- [ ] **Paso 1: prueba que falla.**

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import InicioPage from "./page";
import { useAuth } from "@/lib/auth-context";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));

describe("InicioPage", () => {
  it("explains that the role has no work screen yet", () => {
    vi.mocked(useAuth).mockReturnValue({
      tokenExpiresAt: null,
      proximaExpiracion: false,
      errorRefresh: false,
      renovarSesion: vi.fn(),
      user: { id: "1", rol: "operador_grua", patios: [] },
      token: "t",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    render(<InicioPage />);

    expect(screen.getByRole("heading", { name: /aún no tiene pantalla/i })).toBeInTheDocument();
    expect(screen.getByText("operador_grua")).toBeInTheDocument();
  });
});
```

- [ ] **Paso 2:** correr la prueba. Falla porque la página no existe.
- [ ] **Paso 3:** implementar con `AuthGuard` sin `roles` y el componente `EmptyState` de
  `components/ui`. Revisar las props reales de `EmptyState.tsx` antes de usarlo. Texto:
  título "Tu rol aún no tiene pantalla de trabajo"; cuerpo con el rol en monoespaciado y
  "Pídele a un supervisor lo que necesites mientras la habilitamos."
- [ ] **Paso 4:** prueba en verde.
- [ ] **Paso 5:** commit.

```bash
git add frontend/app/inicio
git commit -m "feat(inicio): pantalla para roles sin pantalla de trabajo"
```

---

## Task 6: Verificación completa

- [ ] `cd frontend && npx tsc --noEmit` sin errores.
- [ ] `cd frontend && npx vitest run` en verde.
- [ ] `cd backend && pytest` en verde.
- [ ] En navegador, con un usuario por rol: cuadrilla llega a Servicios de hoy, guardia a
  Verificar PIN, despachador a Cola de salidas, operador_grua a `/inicio`, cliente a Mis
  contenedores, admin a Patios. Ningún enlace del menú lleva a acceso denegado.
- [ ] Actualizar `context.md`: suites en verde con los nuevos conteos y la tabla de inicio
  por rol.
