# Dashboard Interno (Next.js) — Patio Esperanza — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el dashboard interno en Next.js 14 que consume exclusivamente los endpoints ya existentes del backend (login, patios, contenedores, movimientos, sugerencia de ubicación) para los roles internos (operador, supervisor, admin).

**Architecture:** Next.js 14 App Router, TypeScript, componentes cliente (`"use client"`) para todo lo interactivo — no hay necesidad de server components ya que el backend es una API REST separada con auth JWT del lado del cliente. Sesión JWT guardada en `localStorage` vía un `AuthContext` de React; un componente `AuthGuard` protege cada ruta interna redirigiendo a `/login` si no hay sesión. Estilos con CSS Modules + variables CSS globales (paleta de marca), sin librería de UI externa. Cliente HTTP propio (`lib/api.ts`) tipado a mano contra los schemas reales del backend.

**Tech Stack:** Next.js 14.2.35, React 18.3.1, TypeScript 5.9.3, Vitest 5.0.1 + @testing-library/react 16.3.3 + @testing-library/jest-dom 7.0.1 + @testing-library/user-event 14.6.7 + jsdom 30.1.0 + @vitejs/plugin-react 6.1.1 para tests, ESLint 8.57.1 + eslint-config-next 14.2.35 para lint.

**Fuera de alcance de este plan** (ver spec sección 9-10, roadmap v1 completo vs. lo que el backend ya soporta): portal cliente (solicitudes, ver QR), flujo QR/portería, PWA offline, mapa SVG con drag&drop, CRUD de usuarios/geocercas (admin), API socios. Todo eso requiere endpoints de backend que no existen todavía (`solicitudes`, `qr_tokens`, `escaneos_qr`, `sync_operaciones`, etc. — ver `docs/superpowers/plans/2026-09-14-backend-foundation.md`, sección "Fuera de alcance").

## Global Constraints

- Node.js: usar el mismo runtime ya instalado en la máquina (`v20.20.2` vía nvm). No instalar otra versión.
- Gestor de paquetes: `npm` (coincide con `app.yaml`: `npm ci && npm run build` / `npm start`).
- Directorio del proyecto: `frontend/` en la raíz del repo (coincide con `source_dir: /frontend` de `app.yaml`).
- Versiones exactas a fijar en `package.json` (verificadas contra el registro de npm, no adivinadas):
  - `next@14.2.35`, `react@18.3.1`, `react-dom@18.3.1`
  - `typescript@5.9.3` (se usa la última 5.x, no la 7.x más reciente del registro, porque Next 14 se probó contra TypeScript 5.x)
  - `@types/react@18.3.31`, `@types/react-dom@18.3.7`, `@types/node@26.6.1`
  - `eslint@8.57.1` (última 8.x — `eslint-config-next@14.2.35` exige `eslint: "^7.23.0 || ^8.0.0"`, no es compatible con eslint 9+/10+), `eslint-config-next@14.2.35`
  - `vitest@5.0.1`, `@vitejs/plugin-react@6.1.1`, `jsdom@30.1.0`, `@testing-library/react@16.3.3`, `@testing-library/jest-dom@7.0.1`, `@testing-library/user-event@14.6.7`
- Backend consumido tal cual existe hoy (branch `master` del repo, commit `12cee83` en adelante). No se agregan ni modifican endpoints de backend en este plan.
- `NEXT_PUBLIC_API_URL` es la única forma de configurar la URL del backend (ya está en `app.yaml` para producción). En desarrollo local, `.env.local` con `NEXT_PUBLIC_API_URL=http://localhost:8000`.
- Sesión: JWT crudo en `localStorage` bajo la key `patio_esperanza_token`; decodificado en el cliente (sin librería externa, base64url manual) para leer `sub`/`rol`/`patios` — el backend nunca expone un endpoint `/me`, así que el rol y los patios asignados se leen del propio token.
- Paleta de marca (spec sección 9, aplicar vía variables CSS en `globals.css`): azul `#000056` (navegación/acciones primarias), café `#AF8235` (acentos secundarios), amarillo `#F0D579` (alertas/advertencias, uso exclusivo), gris `#504D4C` (texto secundario/superficies neutras), fondo `#F5F5F7`, superficie `#FFFFFF`, borde `#D8D7DE`, texto `#1B1A1F`.
- Tipografía (spec sección 9): IBM Plex Sans (UI/texto) + IBM Plex Mono (códigos de contenedor, IDs, ubicaciones) vía `next/font/google` — sin `<link>` manual ni paquete adicional.
- Logo: copiar `img/EsperanzaLogo.png` y `img/favicon-180.png` (ya existen en la raíz del repo) a `frontend/public/`. El logo requiere fondo claro (spec sección 9) — nunca colocarlo directo sobre `--azul` sin placa clara detrás.
- Cada componente/página con lógica propia lleva su test en Vitest + React Testing Library junto al archivo fuente (`*.test.tsx` / `*.test.ts` colocado junto al `.tsx`/`.ts`, patrón estándar de Vitest).
- No se guessa ningún nombre de campo de la API: todos los payloads/response shapes de este plan están copiados de los schemas Pydantic reales en `backend/app/schemas/*.py` y `backend/app/api/routes/*.py` (commit `12cee83`).
- Para probar manualmente contra un backend real (no requerido para los tests automatizados, que mockean `fetch`): levantar Postgres (`docker compose up -d db` en la raíz), aplicar migraciones en `patio_dev` (`cd backend && DATABASE_URL=postgresql+asyncpg://patio_app:patio_app@localhost:5433/patio_dev MIGRATIONS_DATABASE_URL=postgresql+asyncpg://patio:patio@localhost:5433/patio_dev alembic upgrade head`, otorgar a `patio_app` los mismos GRANT que en `patio_test` — ver Task 2 y 5 del plan de backend), levantar la API (`uvicorn app.main:app --reload --port 8000`), y sembrar un usuario admin a mano vía `psql` (no existe endpoint de alta de usuarios).

---

## File Structure

```
frontend/                              (nueva, raíz del repo)
├── package.json
├── tsconfig.json
├── next.config.mjs
├── vitest.config.ts
├── vitest.setup.ts
├── .env.local.example
├── public/
│   ├── EsperanzaLogo.png              (copiado de img/)
│   └── favicon-180.png                (copiado de img/)
├── app/
│   ├── layout.tsx                     # fuentes, AuthProvider, NavBar, globals.css
│   ├── globals.css                    # paleta + reset
│   ├── page.tsx                       # redirect a /patios o /login según sesión
│   ├── page.test.tsx
│   ├── login/
│   │   ├── page.tsx
│   │   ├── page.module.css
│   │   └── page.test.tsx
│   ├── patios/
│   │   ├── page.tsx                   # listar + crear (admin)
│   │   ├── page.module.css
│   │   └── page.test.tsx
│   ├── contenedores/
│   │   ├── page.tsx                   # crear contenedor
│   │   ├── page.module.css
│   │   ├── page.test.tsx
│   │   └── [id]/
│   │       ├── page.tsx               # detalle por id
│   │       ├── page.module.css
│   │       └── page.test.tsx
│   ├── movimientos/
│   │   ├── page.tsx                   # registrar movimiento
│   │   ├── page.module.css
│   │   └── page.test.tsx
│   └── ubicaciones/
│       └── sugerir/
│           ├── page.tsx               # sugerencia de ubicación
│           ├── page.module.css
│           └── page.test.tsx
├── components/
│   ├── AuthGuard.tsx
│   ├── AuthGuard.test.tsx
│   ├── NavBar.tsx
│   ├── NavBar.module.css
│   └── NavBar.test.tsx
└── lib/
    ├── jwt.ts
    ├── jwt.test.ts
    ├── auth-context.tsx
    ├── auth-context.test.tsx
    ├── api.ts
    └── api.test.ts
```

---

### Task 1: Scaffold Next.js 14 + TypeScript + Vitest, página estática de humo

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.mjs`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/vitest.setup.ts`
- Create: `frontend/.env.local.example`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/globals.css`
- Create: `frontend/app/page.tsx`
- Test: `frontend/app/page.test.tsx`

**Interfaces:**
- Produces: proyecto Next.js ejecutable (`npm run dev`/`build`), runner de tests (`npm test`), layout raíz sin lógica de auth todavía (se agrega en Task 4).

- [ ] **Step 1: Crear directorio y `package.json`**

```bash
mkdir -p /home/tony/Developer/ProyectoPatioEsperanza/frontend
```

`frontend/package.json`:

```json
{
  "name": "patio-esperanza-web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "vitest run"
  },
  "dependencies": {
    "next": "14.2.35",
    "react": "18.3.1",
    "react-dom": "18.3.1"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "7.0.1",
    "@testing-library/react": "16.3.3",
    "@testing-library/user-event": "14.6.7",
    "@types/node": "26.6.1",
    "@types/react": "18.3.31",
    "@types/react-dom": "18.3.7",
    "@vitejs/plugin-react": "6.1.1",
    "eslint": "8.57.1",
    "eslint-config-next": "14.2.35",
    "jsdom": "30.1.0",
    "typescript": "5.9.3",
    "vitest": "5.0.1"
  }
}
```

- [ ] **Step 2: `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 3: `frontend/next.config.mjs`**

```js
/** @type {import('next').NextConfig} */
const nextConfig = {};

export default nextConfig;
```

- [ ] **Step 4: `frontend/vitest.config.ts`**

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    globals: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
});
```

- [ ] **Step 5: `frontend/vitest.setup.ts`**

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 6: `frontend/.env.local.example`**

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 7: Instalar dependencias**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm install
```
Esperado: se crean `node_modules/` y `package-lock.json`, sin errores de peer dependencies (eslint 8.57.1 satisface el rango `^7.23.0 || ^8.0.0` de `eslint-config-next`).

- [ ] **Step 8: Escribir test que falla**

`frontend/app/page.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import HomePage from "./page";

describe("HomePage", () => {
  it("renders the app name", () => {
    render(<HomePage />);
    expect(screen.getByRole("heading", { name: "Patio Esperanza" })).toBeInTheDocument();
  });
});
```

- [ ] **Step 9: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/page.test.tsx
```
Esperado: FAIL — `Cannot find module './page'` (no existe `app/page.tsx` todavía).

- [ ] **Step 10: `frontend/app/globals.css`**

```css
:root {
  --azul: #000056;
  --azul-soft: #e4e4f0;
  --cafe: #af8235;
  --cafe-soft: #f3e7d2;
  --amarillo: #f0d579;
  --amarillo-ink: #5c4a08;
  --amarillo-soft: #fbf3dc;
  --gris: #504d4c;
  --bg: #f5f5f7;
  --surface: #ffffff;
  --border: #d8d7de;
  --text: #1b1a1f;
  --text-muted: #5b5960;
  --danger: #b3261e;
  --danger-soft: #fbe4e2;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-plex-sans), system-ui, sans-serif;
}

code,
.mono {
  font-family: var(--font-plex-mono), ui-monospace, monospace;
}

a {
  color: var(--azul);
}

button {
  cursor: pointer;
  font-family: inherit;
}
```

- [ ] **Step 11: `frontend/app/layout.tsx`** (versión mínima de este task, sin `AuthProvider`/`NavBar` todavía — se completa en Task 4)

```tsx
import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-plex-sans",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-mono",
});

export const metadata: Metadata = {
  title: "Patio Esperanza",
  description: "Gestión de patio de contenedores",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={`${plexSans.variable} ${plexMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 12: `frontend/app/page.tsx`**

```tsx
export default function HomePage() {
  return (
    <main>
      <h1>Patio Esperanza</h1>
    </main>
  );
}
```

- [ ] **Step 13: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/page.test.tsx
```
Esperado: PASS (1 test)

- [ ] **Step 14: Confirmar que el build de Next funciona**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm run build
```
Esperado: build exitoso (puede tardar ~30-60s la primera vez).

- [ ] **Step 15: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/package.json frontend/package-lock.json frontend/tsconfig.json \
  frontend/next.config.mjs frontend/vitest.config.ts frontend/vitest.setup.ts \
  frontend/.env.local.example frontend/app/layout.tsx frontend/app/globals.css \
  frontend/app/page.tsx frontend/app/page.test.tsx frontend/.gitignore frontend/next-env.d.ts
git commit -m "feat: scaffold Next.js 14 + TypeScript + Vitest para el dashboard"
```
Nota: `frontend/.gitignore` y `frontend/next-env.d.ts` los genera `next build`/`next dev` automáticamente la primera vez; si `next-env.d.ts` no existe aún tras el build, créalo vacío con el contenido estándar:
```
/// <reference types="next" />
/// <reference types="next/image-types/global" />
```

---

### Task 2: Cliente HTTP tipado (`lib/api.ts`) — login

**Files:**
- Create: `frontend/lib/api.ts`
- Test: `frontend/lib/api.test.ts`

**Interfaces:**
- Produces: `ApiError` (clase, `status: number`), `login(username, password) -> Promise<TokenResponse>`, `TokenResponse { access_token: string; token_type: string }`. Estas firmas las consumen las Tasks 3, 5, 6, 7, 8.
- Consumes: `NEXT_PUBLIC_API_URL` (env var, Task 1).

- [ ] **Step 1: Escribir test que falla**

`frontend/lib/api.test.ts`:

```ts
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { login, ApiError } from "./api";

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

describe("login", () => {
  it("posts form-encoded credentials and returns the token", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ access_token: "abc.def.ghi", token_type: "bearer" }),
    });

    const result = await login("admin@patio.mx", "clave123");

    expect(result).toEqual({ access_token: "abc.def.ghi", token_type: "bearer" });
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/auth/login");
    expect(options.method).toBe("POST");
    expect((options.body as URLSearchParams).toString()).toBe(
      "username=admin%40patio.mx&password=clave123"
    );
  });

  it("throws ApiError with the backend detail on failure", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: async () => ({ detail: "Credenciales inválidas" }),
    });

    await expect(login("admin@patio.mx", "mala")).rejects.toThrow(ApiError);
    await expect(login("admin@patio.mx", "mala")).rejects.toThrow("Credenciales inválidas");
  });
});
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- lib/api.test.ts
```
Esperado: FAIL — `Cannot find module './api'`

- [ ] **Step 3: `frontend/lib/api.ts`**

```ts
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit & { token?: string } = {}
): Promise<T> {
  const { token, headers, body, ...rest } = options;
  const isFormBody = body instanceof URLSearchParams;

  const response = await fetch(`${API_URL}${path}`, {
    ...rest,
    body,
    headers: {
      ...(body && !isFormBody ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const errorBody = await response.json();
      detail = errorBody.detail ?? detail;
    } catch {
      // sin cuerpo JSON en la respuesta de error
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export async function login(username: string, password: string): Promise<TokenResponse> {
  const body = new URLSearchParams({ username, password });
  return request<TokenResponse>("/api/auth/login", { method: "POST", body });
}
```

- [ ] **Step 4: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- lib/api.test.ts
```
Esperado: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/lib/api.ts frontend/lib/api.test.ts
git commit -m "feat: cliente HTTP tipado con login()"
```

---

### Task 3: `AuthContext` + decodificación de JWT + página de login

**Files:**
- Create: `frontend/lib/jwt.ts`
- Test: `frontend/lib/jwt.test.ts`
- Create: `frontend/lib/auth-context.tsx`
- Test: `frontend/lib/auth-context.test.tsx`
- Create: `frontend/app/login/page.tsx`
- Create: `frontend/app/login/page.module.css`
- Test: `frontend/app/login/page.test.tsx`

**Interfaces:**
- Produces: `decodeJwtPayload(token) -> JwtPayload` (`{ sub, rol, patios, iat, exp }`), `AuthProvider`, `useAuth() -> { user: AuthUser | null; token: string | null; ready: boolean; setToken(t): void; logout(): void }`, `AuthUser { id, rol, patios: string[] }`. Consumidas por Tasks 4-8.
- Consumes: `login` (Task 2).

- [ ] **Step 1: Escribir test que falla — `jwt.ts`**

`frontend/lib/jwt.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { decodeJwtPayload } from "./jwt";

describe("decodeJwtPayload", () => {
  it("decodes the payload segment of a JWT", () => {
    const payload = { sub: "usr-1", rol: "admin", patios: ["patio-1"], iat: 0, exp: 9999999999 };
    const token = `${btoa("{}")}.${btoa(JSON.stringify(payload))}.signature`;

    expect(decodeJwtPayload(token)).toEqual(payload);
  });
});
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- lib/jwt.test.ts
```
Esperado: FAIL — `Cannot find module './jwt'`

- [ ] **Step 3: `frontend/lib/jwt.ts`**

```ts
export interface JwtPayload {
  sub: string;
  rol: string;
  patios: string[];
  iat: number;
  exp: number;
}

export function decodeJwtPayload(token: string): JwtPayload {
  const base64Url = token.split(".")[1];
  const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
  const json = atob(base64);
  return JSON.parse(json) as JwtPayload;
}
```

- [ ] **Step 4: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- lib/jwt.test.ts
```
Esperado: PASS (1 test)

- [ ] **Step 5: Escribir test que falla — `auth-context.tsx`**

`frontend/lib/auth-context.test.tsx`:

```tsx
import { beforeEach, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider, useAuth } from "./auth-context";

const FAKE_PAYLOAD = { sub: "usr-1", rol: "admin", patios: ["patio-1"], iat: 0, exp: 9999999999 };
const FAKE_TOKEN = `${btoa("{}")}.${btoa(JSON.stringify(FAKE_PAYLOAD))}.signature`;

function TestConsumer() {
  const { user, setToken, logout } = useAuth();
  return (
    <div>
      <span data-testid="rol">{user?.rol ?? "sin-sesion"}</span>
      <button onClick={() => setToken(FAKE_TOKEN)}>login</button>
      <button onClick={logout}>logout</button>
    </div>
  );
}

beforeEach(() => {
  localStorage.clear();
});

describe("AuthProvider", () => {
  it("starts with no user and updates after setToken", async () => {
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    expect(screen.getByTestId("rol").textContent).toBe("sin-sesion");

    await user.click(screen.getByText("login"));

    expect(screen.getByTestId("rol").textContent).toBe("admin");
    expect(localStorage.getItem("patio_esperanza_token")).toBe(FAKE_TOKEN);
  });

  it("restores the session from localStorage on mount", () => {
    localStorage.setItem("patio_esperanza_token", FAKE_TOKEN);

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    expect(screen.getByTestId("rol").textContent).toBe("admin");
  });

  it("clears the session on logout", async () => {
    const user = userEvent.setup();
    localStorage.setItem("patio_esperanza_token", FAKE_TOKEN);
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await user.click(screen.getByText("logout"));

    expect(screen.getByTestId("rol").textContent).toBe("sin-sesion");
    expect(localStorage.getItem("patio_esperanza_token")).toBeNull();
  });
});
```

- [ ] **Step 6: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- lib/auth-context.test.tsx
```
Esperado: FAIL — `Cannot find module './auth-context'`

- [ ] **Step 7: `frontend/lib/auth-context.tsx`**

```tsx
"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { decodeJwtPayload } from "./jwt";

export interface AuthUser {
  id: string;
  rol: string;
  patios: string[];
}

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  ready: boolean;
  setToken: (token: string) => void;
  logout: () => void;
}

const STORAGE_KEY = "patio_esperanza_token";

const AuthContext = createContext<AuthContextValue | null>(null);

function userFromToken(token: string): AuthUser {
  const payload = decodeJwtPayload(token);
  return { id: payload.sub, rol: payload.rol, patios: payload.patios };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      setTokenState(stored);
    }
    setReady(true);
  }, []);

  const setToken = useCallback((next: string) => {
    localStorage.setItem(STORAGE_KEY, next);
    setTokenState(next);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setTokenState(null);
  }, []);

  const user = useMemo(() => (token ? userFromToken(token) : null), [token]);

  const value = useMemo(
    () => ({ user, token, ready, setToken, logout }),
    [user, token, ready, setToken, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
```

- [ ] **Step 8: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- lib/auth-context.test.tsx
```
Esperado: PASS (3 tests)

- [ ] **Step 9: Escribir test que falla — página de login**

`frontend/app/login/page.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LoginPage from "./page";
import { AuthProvider } from "@/lib/auth-context";
import { login, ApiError } from "@/lib/api";

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, login: vi.fn() };
});

const FAKE_PAYLOAD = { sub: "usr-1", rol: "admin", patios: [], iat: 0, exp: 9999999999 };
const FAKE_TOKEN = `${btoa("{}")}.${btoa(JSON.stringify(FAKE_PAYLOAD))}.sig`;

beforeEach(() => {
  localStorage.clear();
  pushMock.mockClear();
  vi.mocked(login).mockReset();
});

describe("LoginPage", () => {
  it("logs in and redirects to /patios", async () => {
    const user = userEvent.setup();
    vi.mocked(login).mockResolvedValue({ access_token: FAKE_TOKEN, token_type: "bearer" });

    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    await user.type(screen.getByLabelText("Correo"), "admin@patio.mx");
    await user.type(screen.getByLabelText("Contraseña"), "clave123");
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/patios"));
  });

  it("shows the backend error message on failed login", async () => {
    const user = userEvent.setup();
    vi.mocked(login).mockRejectedValue(new ApiError(401, "Credenciales inválidas"));

    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    await user.type(screen.getByLabelText("Correo"), "admin@patio.mx");
    await user.type(screen.getByLabelText("Contraseña"), "mala");
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Credenciales inválidas");
  });
});
```

- [ ] **Step 10: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/login/page.test.tsx
```
Esperado: FAIL — `Cannot find module './page'`

- [ ] **Step 11: `frontend/app/login/page.module.css`**

```css
.main {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
}

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 32px;
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.card h1 {
  color: var(--azul);
  font-size: 1.3rem;
  margin: 0 0 12px;
}

.card input {
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 0.9rem;
}

.card button {
  margin-top: 8px;
  background: var(--azul);
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 10px;
  font-weight: 600;
}

.card button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error {
  color: var(--danger);
  background: var(--danger-soft);
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 0.85rem;
  margin: 0;
}
```

- [ ] **Step 12: `frontend/app/login/page.tsx`**

```tsx
"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { login, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import styles from "./page.module.css";

export default function LoginPage() {
  const router = useRouter();
  const { setToken } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const { access_token } = await login(email, password);
      setToken(access_token);
      router.push("/patios");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo iniciar sesión");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className={styles.main}>
      <form className={styles.card} onSubmit={handleSubmit}>
        <h1>Patio Esperanza</h1>
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
        />
        {error && (
          <p role="alert" className={styles.error}>
            {error}
          </p>
        )}
        <button type="submit" disabled={submitting}>
          {submitting ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </main>
  );
}
```

- [ ] **Step 13: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/login/page.test.tsx
```
Esperado: PASS (2 tests)

- [ ] **Step 14: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/lib/jwt.ts frontend/lib/jwt.test.ts frontend/lib/auth-context.tsx \
  frontend/lib/auth-context.test.tsx frontend/app/login
git commit -m "feat: AuthContext con sesion en localStorage + pagina de login"
```

---

### Task 4: `AuthGuard`, `NavBar` con logo, layout raíz completo, redirect en `/`

**Files:**
- Create: `frontend/components/AuthGuard.tsx`
- Test: `frontend/components/AuthGuard.test.tsx`
- Create: `frontend/components/NavBar.tsx`
- Create: `frontend/components/NavBar.module.css`
- Test: `frontend/components/NavBar.test.tsx`
- Modify: `frontend/app/layout.tsx`
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/app/page.test.tsx`
- Create: `frontend/public/EsperanzaLogo.png` (copiado)
- Create: `frontend/public/favicon-180.png` (copiado)

**Interfaces:**
- Produces: `AuthGuard` (componente que envuelve páginas protegidas), `NavBar` (usa `useAuth`). Consumidas por Tasks 5-8.
- Consumes: `useAuth` (Task 3).

- [ ] **Step 1: Copiar los assets del logo**

```bash
mkdir -p /home/tony/Developer/ProyectoPatioEsperanza/frontend/public
cp /home/tony/Developer/ProyectoPatioEsperanza/img/EsperanzaLogo.png \
   /home/tony/Developer/ProyectoPatioEsperanza/frontend/public/EsperanzaLogo.png
cp /home/tony/Developer/ProyectoPatioEsperanza/img/favicon-180.png \
   /home/tony/Developer/ProyectoPatioEsperanza/frontend/public/favicon-180.png
```

- [ ] **Step 2: Escribir test que falla — `AuthGuard`**

`frontend/components/AuthGuard.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { AuthGuard } from "./AuthGuard";
import { useAuth } from "@/lib/auth-context";

const { replaceMock } = vi.hoisted(() => ({ replaceMock: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
}));

vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));

beforeEach(() => {
  replaceMock.mockClear();
  vi.mocked(useAuth).mockReset();
});

describe("AuthGuard", () => {
  it("renders children when there is a session", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "admin", patios: [] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    render(
      <AuthGuard>
        <p>contenido protegido</p>
      </AuthGuard>
    );

    expect(screen.getByText("contenido protegido")).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("redirects to /login when there is no session", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      token: null,
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    render(
      <AuthGuard>
        <p>contenido protegido</p>
      </AuthGuard>
    );

    expect(screen.queryByText("contenido protegido")).not.toBeInTheDocument();
    expect(replaceMock).toHaveBeenCalledWith("/login");
  });

  it("renders nothing while the session is not ready yet", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      token: null,
      ready: false,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    const { container } = render(
      <AuthGuard>
        <p>contenido protegido</p>
      </AuthGuard>
    );

    expect(container).toBeEmptyDOMElement();
    expect(replaceMock).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 3: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- components/AuthGuard.test.tsx
```
Esperado: FAIL — `Cannot find module './AuthGuard'`

- [ ] **Step 4: `frontend/components/AuthGuard.tsx`**

```tsx
"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export function AuthGuard({ children }: { children: ReactNode }) {
  const { user, ready } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (ready && !user) {
      router.replace("/login");
    }
  }, [ready, user, router]);

  if (!ready || !user) {
    return null;
  }

  return <>{children}</>;
}
```

- [ ] **Step 5: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- components/AuthGuard.test.tsx
```
Esperado: PASS (3 tests)

- [ ] **Step 6: Escribir test que falla — `NavBar`**

`frontend/components/NavBar.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NavBar } from "./NavBar";
import { useAuth } from "@/lib/auth-context";

vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));

beforeEach(() => {
  vi.mocked(useAuth).mockReset();
});

describe("NavBar", () => {
  it("renders nothing when there is no session", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      token: null,
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    const { container } = render(<NavBar />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the role and calls logout on click", async () => {
    const logoutMock = vi.fn();
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "operador", patios: [] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: logoutMock,
    });

    const user = userEvent.setup();
    render(<NavBar />);

    expect(screen.getByText("operador")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Salir" }));
    expect(logoutMock).toHaveBeenCalled();
  });
});
```

- [ ] **Step 7: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- components/NavBar.test.tsx
```
Esperado: FAIL — `Cannot find module './NavBar'`

- [ ] **Step 8: `frontend/components/NavBar.module.css`**

```css
.nav {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 12px 24px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}

.brand {
  display: flex;
  align-items: center;
}

.links {
  display: flex;
  gap: 16px;
  flex: 1;
}

.session {
  display: flex;
  align-items: center;
  gap: 12px;
}

.rol {
  font-family: var(--font-plex-mono), monospace;
  font-size: 0.78rem;
  text-transform: uppercase;
  color: var(--text-muted);
}

.session button {
  background: var(--azul);
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 6px 14px;
}
```

- [ ] **Step 9: `frontend/components/NavBar.tsx`**

```tsx
"use client";

import Link from "next/link";
import Image from "next/image";
import { useAuth } from "@/lib/auth-context";
import styles from "./NavBar.module.css";

export function NavBar() {
  const { user, logout } = useAuth();

  if (!user) {
    return null;
  }

  return (
    <nav className={styles.nav}>
      <Link href="/patios" className={styles.brand}>
        <Image src="/EsperanzaLogo.png" alt="Patio Esperanza" width={140} height={93} priority />
      </Link>
      <div className={styles.links}>
        <Link href="/patios">Patios</Link>
        <Link href="/contenedores">Contenedores</Link>
        <Link href="/movimientos">Movimientos</Link>
        <Link href="/ubicaciones/sugerir">Sugerir ubicación</Link>
      </div>
      <div className={styles.session}>
        <span className={styles.rol}>{user.rol}</span>
        <button onClick={logout}>Salir</button>
      </div>
    </nav>
  );
}
```

- [ ] **Step 10: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- components/NavBar.test.tsx
```
Esperado: PASS (2 tests)

- [ ] **Step 11: Escribir test que falla — redirect en `/`**

Reemplazar `frontend/app/page.test.tsx` completo:

```tsx
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";
import HomePage from "./page";
import { useAuth } from "@/lib/auth-context";

const { replaceMock } = vi.hoisted(() => ({ replaceMock: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
}));

vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));

beforeEach(() => {
  replaceMock.mockClear();
  vi.mocked(useAuth).mockReset();
});

describe("HomePage", () => {
  it("redirects to /patios when authenticated", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "admin", patios: [] },
      token: "t",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    render(<HomePage />);

    expect(replaceMock).toHaveBeenCalledWith("/patios");
  });

  it("redirects to /login when not authenticated", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      token: null,
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    render(<HomePage />);

    expect(replaceMock).toHaveBeenCalledWith("/login");
  });

  it("does nothing while the session is not ready", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      token: null,
      ready: false,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    render(<HomePage />);

    expect(replaceMock).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 12: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/page.test.tsx
```
Esperado: FAIL — el `HomePage` actual (Task 1) renderiza un `<h1>`, no llama a `router.replace`.

- [ ] **Step 13: Reemplazar `frontend/app/page.tsx`**

```tsx
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export default function HomePage() {
  const { user, ready } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!ready) return;
    router.replace(user ? "/patios" : "/login");
  }, [ready, user, router]);

  return null;
}
```

- [ ] **Step 14: Reemplazar `frontend/app/layout.tsx`** (agrega `AuthProvider` y `NavBar`)

```tsx
import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import { AuthProvider } from "@/lib/auth-context";
import { NavBar } from "@/components/NavBar";
import "./globals.css";

const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-plex-sans",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-mono",
});

export const metadata: Metadata = {
  title: "Patio Esperanza",
  description: "Gestión de patio de contenedores",
  icons: { apple: "/favicon-180.png" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={`${plexSans.variable} ${plexMono.variable}`}>
      <body>
        <AuthProvider>
          <NavBar />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
```

- [ ] **Step 15: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/page.test.tsx
```
Esperado: PASS (3 tests)

- [ ] **Step 16: Correr toda la suite de frontend**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test
```
Esperado: PASS (todos los tests hasta este punto)

- [ ] **Step 17: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/components frontend/app/layout.tsx frontend/app/page.tsx \
  frontend/app/page.test.tsx frontend/public
git commit -m "feat: AuthGuard, NavBar con logo, redirect segun sesion en /"
```

---

### Task 5: Página de Patios (listar + crear, admin)

**Files:**
- Create: `frontend/app/patios/page.tsx`
- Create: `frontend/app/patios/page.module.css`
- Test: `frontend/app/patios/page.test.tsx`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/api.test.ts`

**Interfaces:**
- Produces (agregado a `lib/api.ts`): `Patio { id, nombre, codigo, activo }`, `listPatios(token) -> Promise<Patio[]>`, `createPatio(token, { nombre, codigo }) -> Promise<Patio>`.
- Consumes: `AuthGuard`, `useAuth` (Task 4); `request`/`ApiError` (Task 2).
- Corresponde a `GET /api/patios` y `POST /api/patios` en `backend/app/api/routes/patios.py`.

- [ ] **Step 1: Escribir tests que fallan — `lib/api.ts`**

Agregar a `frontend/lib/api.test.ts` (al final del archivo, mismo `describe` de nivel superior):

```ts
import { createPatio, listPatios, type Patio } from "./api";

describe("listPatios", () => {
  it("sends the bearer token and returns the list", async () => {
    const patios: Patio[] = [{ id: "1", nombre: "Patio Norte", codigo: "PN", activo: true }];
    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => patios });

    const result = await listPatios("token-123");

    expect(result).toEqual(patios);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/patios");
    expect(options.headers.Authorization).toBe("Bearer token-123");
  });
});

describe("createPatio", () => {
  it("posts the payload as JSON with the bearer token", async () => {
    const creado: Patio = { id: "2", nombre: "Patio Sur", codigo: "PS", activo: true };
    fetchMock.mockResolvedValue({ ok: true, status: 201, json: async () => creado });

    const result = await createPatio("token-123", { nombre: "Patio Sur", codigo: "PS" });

    expect(result).toEqual(creado);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/patios");
    expect(options.method).toBe("POST");
    expect(options.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(options.body as string)).toEqual({ nombre: "Patio Sur", codigo: "PS" });
  });
});
```

Nota: mueve el `import { login, ApiError } from "./api";` existente y agrega los nuevos imports junto a él, o combínalos en una sola línea `import { login, ApiError, listPatios, createPatio, type Patio } from "./api";` al inicio del archivo.

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- lib/api.test.ts
```
Esperado: FAIL — `listPatios`/`createPatio` no existen todavía en `./api`.

- [ ] **Step 3: Agregar a `frontend/lib/api.ts`** (al final del archivo)

```ts
export interface Patio {
  id: string;
  nombre: string;
  codigo: string;
  activo: boolean;
}

export async function listPatios(token: string): Promise<Patio[]> {
  return request<Patio[]>("/api/patios", { token });
}

export async function createPatio(
  token: string,
  payload: { nombre: string; codigo: string }
): Promise<Patio> {
  return request<Patio>("/api/patios", {
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
Esperado: PASS (4 tests)

- [ ] **Step 5: Escribir test que falla — página de patios**

`frontend/app/patios/page.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PatiosPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { listPatios, createPatio } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, listPatios: vi.fn(), createPatio: vi.fn() };
});

function mockAuth(rol: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "1", rol, patios: [] },
    token: "token",
    ready: true,
    setToken: vi.fn(),
    logout: vi.fn(),
  });
}

beforeEach(() => {
  vi.mocked(listPatios).mockReset();
  vi.mocked(createPatio).mockReset();
});

describe("PatiosPage", () => {
  it("lists the patios returned by the backend", async () => {
    mockAuth("operador");
    vi.mocked(listPatios).mockResolvedValue([
      { id: "1", nombre: "Patio Norte", codigo: "PN", activo: true },
    ]);

    render(<PatiosPage />);

    expect(await screen.findByText(/Patio Norte/)).toBeInTheDocument();
  });

  it("hides the create form for non-admin roles", async () => {
    mockAuth("operador");
    vi.mocked(listPatios).mockResolvedValue([]);

    render(<PatiosPage />);

    await waitFor(() => expect(listPatios).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: "Crear patio" })).not.toBeInTheDocument();
  });

  it("lets an admin create a patio and refreshes the list", async () => {
    mockAuth("admin");
    vi.mocked(listPatios)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([{ id: "2", nombre: "Patio Sur", codigo: "PS", activo: true }]);
    vi.mocked(createPatio).mockResolvedValue({
      id: "2",
      nombre: "Patio Sur",
      codigo: "PS",
      activo: true,
    });

    const user = userEvent.setup();
    render(<PatiosPage />);

    await screen.findByRole("button", { name: "Crear patio" });
    await user.type(screen.getByLabelText("Nombre"), "Patio Sur");
    await user.type(screen.getByLabelText("Código"), "PS");
    await user.click(screen.getByRole("button", { name: "Crear patio" }));

    expect(createPatio).toHaveBeenCalledWith("token", { nombre: "Patio Sur", codigo: "PS" });
    expect(await screen.findByText(/Patio Sur/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 6: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/patios/page.test.tsx
```
Esperado: FAIL — `Cannot find module './page'`

- [ ] **Step 7: `frontend/app/patios/page.module.css`**

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

.form input {
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
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

- [ ] **Step 8: `frontend/app/patios/page.tsx`**

```tsx
"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import { ApiError, createPatio, listPatios, type Patio } from "@/lib/api";
import styles from "./page.module.css";

function PatiosContent() {
  const { token, user } = useAuth();
  const [patios, setPatios] = useState<Patio[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nombre, setNombre] = useState("");
  const [codigo, setCodigo] = useState("");
  const [creating, setCreating] = useState(false);

  const cargarPatios = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await listPatios(token);
      setPatios(data);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar los patios");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    cargarPatios();
  }, [cargarPatios]);

  async function handleCrear(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setCreating(true);
    setError(null);
    try {
      await createPatio(token, { nombre, codigo });
      setNombre("");
      setCodigo("");
      await cargarPatios();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el patio");
    } finally {
      setCreating(false);
    }
  }

  return (
    <main className={styles.main}>
      <h1>Patios</h1>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      {loading ? (
        <p>Cargando...</p>
      ) : (
        <ul className={styles.list}>
          {patios.map((patio) => (
            <li key={patio.id}>
              <span className="mono">{patio.codigo}</span> — {patio.nombre}
            </li>
          ))}
        </ul>
      )}

      {user?.rol === "admin" && (
        <form className={styles.form} onSubmit={handleCrear}>
          <h2>Nuevo patio</h2>
          <label htmlFor="nombre">Nombre</label>
          <input id="nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
          <label htmlFor="codigo">Código</label>
          <input id="codigo" value={codigo} onChange={(e) => setCodigo(e.target.value)} required />
          <button type="submit" disabled={creating}>
            {creating ? "Creando..." : "Crear patio"}
          </button>
        </form>
      )}
    </main>
  );
}

export default function PatiosPage() {
  return (
    <AuthGuard>
      <PatiosContent />
    </AuthGuard>
  );
}
```

- [ ] **Step 9: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/patios/page.test.tsx
```
Esperado: PASS (3 tests)

- [ ] **Step 10: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/lib/api.ts frontend/lib/api.test.ts frontend/app/patios
git commit -m "feat: pagina de patios (listar + crear para admin)"
```

---

### Task 6: Contenedores — crear + detalle por ID

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/api.test.ts`
- Create: `frontend/app/contenedores/page.tsx`
- Create: `frontend/app/contenedores/page.module.css`
- Test: `frontend/app/contenedores/page.test.tsx`
- Create: `frontend/app/contenedores/[id]/page.tsx`
- Create: `frontend/app/contenedores/[id]/page.module.css`
- Test: `frontend/app/contenedores/[id]/page.test.tsx`

**Interfaces:**
- Produces (agregado a `lib/api.ts`): `TipoContenedor = "lleno" | "vacio"`, `TamanoContenedor = "20" | "40" | "45"`, `EstadoContenedor` (unión de los 12 valores de `backend/app/models/enums.py::EstadoContenedor`), `Contenedor { id, numero_contenedor, tipo, tamano, patio_id, estado, peso_kg }`, `createContenedor(token, payload) -> Promise<Contenedor>`, `getContenedor(token, id) -> Promise<Contenedor>`.
- Consumes: `AuthGuard`, `useAuth` (Task 4).
- Corresponde a `POST /api/contenedores` y `GET /api/contenedores/{id}` en `backend/app/api/routes/contenedores.py`.

- [ ] **Step 1: Escribir tests que fallan — `lib/api.ts`**

Agregar a `frontend/lib/api.test.ts`:

```ts
import { createContenedor, getContenedor, type Contenedor } from "./api";

const CONTENEDOR: Contenedor = {
  id: "c1",
  numero_contenedor: "CSQU3054383",
  tipo: "lleno",
  tamano: "40",
  patio_id: "p1",
  estado: "solicitud_ingreso",
  peso_kg: 18000,
};

describe("createContenedor", () => {
  it("posts the payload as JSON", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 201, json: async () => CONTENEDOR });

    const result = await createContenedor("token-123", {
      numero_contenedor: "CSQU3054383",
      tipo: "lleno",
      tamano: "40",
      patio_id: "p1",
      peso_kg: 18000,
    });

    expect(result).toEqual(CONTENEDOR);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/contenedores");
    expect(options.method).toBe("POST");
  });
});

describe("getContenedor", () => {
  it("gets a contenedor by id", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => CONTENEDOR });

    const result = await getContenedor("token-123", "c1");

    expect(result).toEqual(CONTENEDOR);
    const [url] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/contenedores/c1");
  });
});
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- lib/api.test.ts
```
Esperado: FAIL — `createContenedor`/`getContenedor` no existen.

- [ ] **Step 3: Agregar a `frontend/lib/api.ts`**

```ts
export type TipoContenedor = "lleno" | "vacio";
export type TamanoContenedor = "20" | "40" | "45";
export type EstadoContenedor =
  | "solicitud_ingreso"
  | "qr_ingreso_emitido"
  | "en_porteria"
  | "ingresado"
  | "ubicado"
  | "en_estadia"
  | "en_servicio_especial"
  | "solicitud_salida"
  | "qr_salida_emitido"
  | "en_porteria_salida"
  | "despachado"
  | "rechazado";

export interface Contenedor {
  id: string;
  numero_contenedor: string;
  tipo: TipoContenedor;
  tamano: TamanoContenedor;
  patio_id: string;
  estado: EstadoContenedor;
  peso_kg: number;
}

export async function createContenedor(
  token: string,
  payload: {
    numero_contenedor: string;
    tipo: TipoContenedor;
    tamano: TamanoContenedor;
    patio_id: string;
    peso_kg: number;
  }
): Promise<Contenedor> {
  return request<Contenedor>("/api/contenedores", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function getContenedor(token: string, id: string): Promise<Contenedor> {
  return request<Contenedor>(`/api/contenedores/${id}`, { token });
}
```

- [ ] **Step 4: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- lib/api.test.ts
```
Esperado: PASS (6 tests)

- [ ] **Step 5: Escribir test que falla — crear contenedor**

`frontend/app/contenedores/page.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ContenedoresPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { createContenedor } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, createContenedor: vi.fn() };
});

beforeEach(() => {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "1", rol: "operador", patios: [] },
    token: "token",
    ready: true,
    setToken: vi.fn(),
    logout: vi.fn(),
  });
  vi.mocked(createContenedor).mockReset();
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
    await user.type(screen.getByLabelText("ID de patio"), "p1");
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
    await user.type(screen.getByLabelText("ID de patio"), "p1");
    await user.type(screen.getByLabelText("Peso (kg)"), "18000");
    await user.click(screen.getByRole("button", { name: "Crear contenedor" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "numero_contenedor no cumple el checksum ISO 6346"
    );
  });
});
```

- [ ] **Step 6: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/contenedores/page.test.tsx
```
Esperado: FAIL — `Cannot find module './page'`

- [ ] **Step 7: `frontend/app/contenedores/page.module.css`**

```css
.main {
  max-width: 480px;
  margin: 32px auto;
  padding: 0 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
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

.ok {
  color: #2e7d46;
  background: #e4f2e8;
  padding: 8px 10px;
  border-radius: 6px;
}
```

- [ ] **Step 8: `frontend/app/contenedores/page.tsx`**

```tsx
"use client";

import { useState, type FormEvent } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import {
  ApiError,
  createContenedor,
  type Contenedor,
  type TamanoContenedor,
  type TipoContenedor,
} from "@/lib/api";
import styles from "./page.module.css";

function ContenedoresContent() {
  const { token } = useAuth();
  const [numero, setNumero] = useState("");
  const [tipo, setTipo] = useState<TipoContenedor>("lleno");
  const [tamano, setTamano] = useState<TamanoContenedor>("40");
  const [patioId, setPatioId] = useState("");
  const [pesoKg, setPesoKg] = useState("");
  const [creado, setCreado] = useState<Contenedor | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setSubmitting(true);
    setError(null);
    setCreado(null);
    try {
      const contenedor = await createContenedor(token, {
        numero_contenedor: numero,
        tipo,
        tamano,
        patio_id: patioId,
        peso_kg: Number(pesoKg),
      });
      setCreado(contenedor);
      setNumero("");
      setPesoKg("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el contenedor");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className={styles.main}>
      <h1>Contenedores</h1>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      {creado && (
        <p className={styles.ok}>
          Creado <span className="mono">{creado.numero_contenedor}</span> — estado{" "}
          {creado.estado}
        </p>
      )}
      <form className={styles.form} onSubmit={handleSubmit}>
        <label htmlFor="numero">Número de contenedor</label>
        <input
          id="numero"
          value={numero}
          onChange={(e) => setNumero(e.target.value)}
          required
          maxLength={11}
        />

        <label htmlFor="tipo">Tipo</label>
        <select id="tipo" value={tipo} onChange={(e) => setTipo(e.target.value as TipoContenedor)}>
          <option value="lleno">Lleno</option>
          <option value="vacio">Vacío</option>
        </select>

        <label htmlFor="tamano">Tamaño</label>
        <select
          id="tamano"
          value={tamano}
          onChange={(e) => setTamano(e.target.value as TamanoContenedor)}
        >
          <option value="20">20&apos;</option>
          <option value="40">40&apos;</option>
          <option value="45">45&apos;</option>
        </select>

        <label htmlFor="patio_id">ID de patio</label>
        <input id="patio_id" value={patioId} onChange={(e) => setPatioId(e.target.value)} required />

        <label htmlFor="peso_kg">Peso (kg)</label>
        <input
          id="peso_kg"
          type="number"
          value={pesoKg}
          onChange={(e) => setPesoKg(e.target.value)}
          required
        />

        <button type="submit" disabled={submitting}>
          {submitting ? "Creando..." : "Crear contenedor"}
        </button>
      </form>
    </main>
  );
}

export default function ContenedoresPage() {
  return (
    <AuthGuard>
      <ContenedoresContent />
    </AuthGuard>
  );
}
```

- [ ] **Step 9: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/contenedores/page.test.tsx
```
Esperado: PASS (2 tests)

- [ ] **Step 10: Escribir test que falla — detalle por ID**

`frontend/app/contenedores/[id]/page.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ContenedorDetallePage from "./page";
import { useAuth } from "@/lib/auth-context";
import { getContenedor, ApiError } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  useParams: () => ({ id: "c1" }),
}));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, getContenedor: vi.fn() };
});

beforeEach(() => {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "1", rol: "operador", patios: [] },
    token: "token",
    ready: true,
    setToken: vi.fn(),
    logout: vi.fn(),
  });
  vi.mocked(getContenedor).mockReset();
});

describe("ContenedorDetallePage", () => {
  it("shows the container fetched by id", async () => {
    vi.mocked(getContenedor).mockResolvedValue({
      id: "c1",
      numero_contenedor: "CSQU3054383",
      tipo: "lleno",
      tamano: "40",
      patio_id: "p1",
      estado: "ubicado",
      peso_kg: 18000,
    });

    render(<ContenedorDetallePage />);

    expect(await screen.findByText("CSQU3054383")).toBeInTheDocument();
    expect(screen.getByText("ubicado")).toBeInTheDocument();
    expect(getContenedor).toHaveBeenCalledWith("token", "c1");
  });

  it("shows an error when the container is not found or hidden by RLS", async () => {
    vi.mocked(getContenedor).mockRejectedValue(new ApiError(404, "Contenedor no encontrado"));

    render(<ContenedorDetallePage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Contenedor no encontrado");
  });
});
```

- [ ] **Step 11: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- "app/contenedores/[id]/page.test.tsx"
```
Esperado: FAIL — `Cannot find module './page'`

- [ ] **Step 12: `frontend/app/contenedores/[id]/page.module.css`**

```css
.main {
  max-width: 480px;
  margin: 32px auto;
  padding: 0 20px;
}

.detalle {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 6px 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}

.detalle dt {
  color: var(--text-muted);
  font-size: 0.82rem;
  text-transform: uppercase;
}

.detalle dd {
  margin: 0;
}

.error {
  color: var(--danger);
  background: var(--danger-soft);
  padding: 8px 10px;
  border-radius: 6px;
}
```

- [ ] **Step 13: `frontend/app/contenedores/[id]/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import { ApiError, getContenedor, type Contenedor } from "@/lib/api";
import styles from "./page.module.css";

function ContenedorDetalleContent() {
  const params = useParams<{ id: string }>();
  const { token } = useAuth();
  const [contenedor, setContenedor] = useState<Contenedor | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    let cancelado = false;
    setLoading(true);
    getContenedor(token, params.id)
      .then((data) => {
        if (!cancelado) setContenedor(data);
      })
      .catch((err) => {
        if (!cancelado) {
          setError(err instanceof ApiError ? err.message : "No se pudo cargar el contenedor");
        }
      })
      .finally(() => {
        if (!cancelado) setLoading(false);
      });
    return () => {
      cancelado = true;
    };
  }, [token, params.id]);

  if (loading) return <p>Cargando...</p>;
  if (error)
    return (
      <p role="alert" className={styles.error}>
        {error}
      </p>
    );
  if (!contenedor) return null;

  return (
    <main className={styles.main}>
      <h1 className="mono">{contenedor.numero_contenedor}</h1>
      <dl className={styles.detalle}>
        <dt>Tipo</dt>
        <dd>{contenedor.tipo}</dd>
        <dt>Tamaño</dt>
        <dd>{contenedor.tamano}&apos;</dd>
        <dt>Estado</dt>
        <dd>{contenedor.estado}</dd>
        <dt>Peso</dt>
        <dd>{contenedor.peso_kg} kg</dd>
      </dl>
    </main>
  );
}

export default function ContenedorDetallePage() {
  return (
    <AuthGuard>
      <ContenedorDetalleContent />
    </AuthGuard>
  );
}
```

- [ ] **Step 14: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- "app/contenedores/[id]/page.test.tsx"
```
Esperado: PASS (2 tests)

- [ ] **Step 15: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/lib/api.ts frontend/lib/api.test.ts frontend/app/contenedores
git commit -m "feat: crear contenedor y ver detalle por id"
```

---

### Task 7: Registrar movimiento

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/api.test.ts`
- Create: `frontend/app/movimientos/page.tsx`
- Create: `frontend/app/movimientos/page.module.css`
- Test: `frontend/app/movimientos/page.test.tsx`

**Interfaces:**
- Produces (agregado a `lib/api.ts`): `TipoMovimiento = "ingreso" | "reubicacion" | "servicio" | "salida"`, `Movimiento { id, contenedor_id, ubicacion_destino_id, tipo }`, `crearMovimiento(token, payload) -> Promise<Movimiento>`.
- Consumes: `AuthGuard`, `useAuth` (Task 4).
- Corresponde a `POST /api/movimientos` en `backend/app/api/routes/movimientos.py`.

- [ ] **Step 1: Escribir test que falla — `lib/api.ts`**

Agregar a `frontend/lib/api.test.ts`:

```ts
import { crearMovimiento, type Movimiento } from "./api";

describe("crearMovimiento", () => {
  it("posts the payload and returns the movimiento", async () => {
    const movimiento: Movimiento = {
      id: "m1",
      contenedor_id: "c1",
      ubicacion_destino_id: "u1",
      tipo: "ingreso",
    };
    fetchMock.mockResolvedValue({ ok: true, status: 201, json: async () => movimiento });

    const result = await crearMovimiento("token-123", {
      contenedor_id: "c1",
      ubicacion_destino_id: "u1",
      tipo: "ingreso",
    });

    expect(result).toEqual(movimiento);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/movimientos");
    expect(options.method).toBe("POST");
  });
});
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- lib/api.test.ts
```
Esperado: FAIL — `crearMovimiento` no existe.

- [ ] **Step 3: Agregar a `frontend/lib/api.ts`**

```ts
export type TipoMovimiento = "ingreso" | "reubicacion" | "servicio" | "salida";

export interface Movimiento {
  id: string;
  contenedor_id: string;
  ubicacion_destino_id: string | null;
  tipo: TipoMovimiento;
}

export async function crearMovimiento(
  token: string,
  payload: {
    contenedor_id: string;
    ubicacion_destino_id: string;
    tipo: TipoMovimiento;
    override_manual?: boolean;
    motivo_override?: string;
  }
): Promise<Movimiento> {
  return request<Movimiento>("/api/movimientos", {
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
Esperado: PASS (7 tests)

- [ ] **Step 5: Escribir test que falla — página de movimientos**

`frontend/app/movimientos/page.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MovimientosPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { crearMovimiento } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, crearMovimiento: vi.fn() };
});

beforeEach(() => {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "1", rol: "operador", patios: [] },
    token: "token",
    ready: true,
    setToken: vi.fn(),
    logout: vi.fn(),
  });
  vi.mocked(crearMovimiento).mockReset();
});

describe("MovimientosPage", () => {
  it("registers a movimiento with the form values", async () => {
    vi.mocked(crearMovimiento).mockResolvedValue({
      id: "m1",
      contenedor_id: "c1",
      ubicacion_destino_id: "u1",
      tipo: "ingreso",
    });

    const user = userEvent.setup();
    render(<MovimientosPage />);

    await user.type(screen.getByLabelText("ID de contenedor"), "c1");
    await user.type(screen.getByLabelText("ID de ubicación destino"), "u1");
    await user.click(screen.getByRole("button", { name: "Registrar movimiento" }));

    expect(crearMovimiento).toHaveBeenCalledWith("token", {
      contenedor_id: "c1",
      ubicacion_destino_id: "u1",
      tipo: "ingreso",
    });
    expect(await screen.findByText(/Movimiento m1 registrado/)).toBeInTheDocument();
  });

  it("shows the backend error when the slot is already occupied", async () => {
    const { ApiError } = await import("@/lib/api");
    vi.mocked(crearMovimiento).mockRejectedValue(new ApiError(409, "Ubicación ya ocupada"));

    const user = userEvent.setup();
    render(<MovimientosPage />);

    await user.type(screen.getByLabelText("ID de contenedor"), "c1");
    await user.type(screen.getByLabelText("ID de ubicación destino"), "u1");
    await user.click(screen.getByRole("button", { name: "Registrar movimiento" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Ubicación ya ocupada");
  });
});
```

- [ ] **Step 6: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/movimientos/page.test.tsx
```
Esperado: FAIL — `Cannot find module './page'`

- [ ] **Step 7: `frontend/app/movimientos/page.module.css`**

```css
.main {
  max-width: 480px;
  margin: 32px auto;
  padding: 0 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
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

.ok {
  color: #2e7d46;
  background: #e4f2e8;
  padding: 8px 10px;
  border-radius: 6px;
}
```

- [ ] **Step 8: `frontend/app/movimientos/page.tsx`**

```tsx
"use client";

import { useState, type FormEvent } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import { ApiError, crearMovimiento, type Movimiento, type TipoMovimiento } from "@/lib/api";
import styles from "./page.module.css";

function MovimientosContent() {
  const { token } = useAuth();
  const [contenedorId, setContenedorId] = useState("");
  const [ubicacionDestinoId, setUbicacionDestinoId] = useState("");
  const [tipo, setTipo] = useState<TipoMovimiento>("ingreso");
  const [creado, setCreado] = useState<Movimiento | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setSubmitting(true);
    setError(null);
    setCreado(null);
    try {
      const movimiento = await crearMovimiento(token, {
        contenedor_id: contenedorId,
        ubicacion_destino_id: ubicacionDestinoId,
        tipo,
      });
      setCreado(movimiento);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo registrar el movimiento");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className={styles.main}>
      <h1>Registrar movimiento</h1>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      {creado && <p className={styles.ok}>Movimiento {creado.id} registrado</p>}
      <form className={styles.form} onSubmit={handleSubmit}>
        <label htmlFor="contenedor_id">ID de contenedor</label>
        <input
          id="contenedor_id"
          value={contenedorId}
          onChange={(e) => setContenedorId(e.target.value)}
          required
        />

        <label htmlFor="ubicacion_destino_id">ID de ubicación destino</label>
        <input
          id="ubicacion_destino_id"
          value={ubicacionDestinoId}
          onChange={(e) => setUbicacionDestinoId(e.target.value)}
          required
        />

        <label htmlFor="tipo">Tipo de movimiento</label>
        <select id="tipo" value={tipo} onChange={(e) => setTipo(e.target.value as TipoMovimiento)}>
          <option value="ingreso">Ingreso</option>
          <option value="reubicacion">Reubicación</option>
          <option value="servicio">Servicio</option>
          <option value="salida">Salida</option>
        </select>

        <button type="submit" disabled={submitting}>
          {submitting ? "Registrando..." : "Registrar movimiento"}
        </button>
      </form>
    </main>
  );
}

export default function MovimientosPage() {
  return (
    <AuthGuard>
      <MovimientosContent />
    </AuthGuard>
  );
}
```

- [ ] **Step 9: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/movimientos/page.test.tsx
```
Esperado: PASS (2 tests)

- [ ] **Step 10: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/lib/api.ts frontend/lib/api.test.ts frontend/app/movimientos
git commit -m "feat: registrar movimiento de contenedor"
```

---

### Task 8: Sugerencia de ubicación

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/api.test.ts`
- Create: `frontend/app/ubicaciones/sugerir/page.tsx`
- Create: `frontend/app/ubicaciones/sugerir/page.module.css`
- Test: `frontend/app/ubicaciones/sugerir/page.test.tsx`

**Interfaces:**
- Produces (agregado a `lib/api.ts`): `SugerenciaUbicacion { ubicacion_id, codigo, costo }`, `sugerirUbicacion(token, { patio_id, contenedor_id, punto_referencia_ubicacion_id }) -> Promise<SugerenciaUbicacion>`.
- Consumes: `AuthGuard`, `useAuth` (Task 4).
- Corresponde a `POST /api/ubicaciones/sugerir` en `backend/app/api/routes/ubicaciones.py`.

- [ ] **Step 1: Escribir test que falla — `lib/api.ts`**

Agregar a `frontend/lib/api.test.ts`:

```ts
import { sugerirUbicacion, type SugerenciaUbicacion } from "./api";

describe("sugerirUbicacion", () => {
  it("posts the payload and returns the suggestion", async () => {
    const sugerencia: SugerenciaUbicacion = {
      ubicacion_id: "u1",
      codigo: "A1-T1-S1-N1",
      costo: 1.3,
    };
    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => sugerencia });

    const result = await sugerirUbicacion("token-123", {
      patio_id: "p1",
      contenedor_id: "c1",
      punto_referencia_ubicacion_id: "u0",
    });

    expect(result).toEqual(sugerencia);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/ubicaciones/sugerir");
    expect(options.method).toBe("POST");
  });
});
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- lib/api.test.ts
```
Esperado: FAIL — `sugerirUbicacion` no existe.

- [ ] **Step 3: Agregar a `frontend/lib/api.ts`**

```ts
export interface SugerenciaUbicacion {
  ubicacion_id: string;
  codigo: string;
  costo: number;
}

export async function sugerirUbicacion(
  token: string,
  payload: { patio_id: string; contenedor_id: string; punto_referencia_ubicacion_id: string }
): Promise<SugerenciaUbicacion> {
  return request<SugerenciaUbicacion>("/api/ubicaciones/sugerir", {
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
Esperado: PASS (8 tests)

- [ ] **Step 5: Escribir test que falla — página de sugerencia**

`frontend/app/ubicaciones/sugerir/page.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SugerirUbicacionPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { sugerirUbicacion } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, sugerirUbicacion: vi.fn() };
});

beforeEach(() => {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "1", rol: "operador", patios: [] },
    token: "token",
    ready: true,
    setToken: vi.fn(),
    logout: vi.fn(),
  });
  vi.mocked(sugerirUbicacion).mockReset();
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

    await user.type(screen.getByLabelText("ID de patio"), "p1");
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

    await user.type(screen.getByLabelText("ID de patio"), "p1");
    await user.type(screen.getByLabelText("ID de contenedor"), "c1");
    await user.type(screen.getByLabelText("ID de ubicación de referencia"), "u0");
    await user.click(screen.getByRole("button", { name: "Sugerir" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No hay ubicaciones disponibles que cumplan las restricciones"
    );
  });
});
```

- [ ] **Step 6: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/ubicaciones/sugerir/page.test.tsx
```
Esperado: FAIL — `Cannot find module './page'`

- [ ] **Step 7: `frontend/app/ubicaciones/sugerir/page.module.css`**

```css
.main {
  max-width: 480px;
  margin: 32px auto;
  padding: 0 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
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

.form input {
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
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

.ok {
  color: #2e7d46;
  background: #e4f2e8;
  padding: 8px 10px;
  border-radius: 6px;
}
```

- [ ] **Step 8: `frontend/app/ubicaciones/sugerir/page.tsx`**

```tsx
"use client";

import { useState, type FormEvent } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import { ApiError, sugerirUbicacion, type SugerenciaUbicacion } from "@/lib/api";
import styles from "./page.module.css";

function SugerirUbicacionContent() {
  const { token } = useAuth();
  const [patioId, setPatioId] = useState("");
  const [contenedorId, setContenedorId] = useState("");
  const [puntoReferenciaId, setPuntoReferenciaId] = useState("");
  const [resultado, setResultado] = useState<SugerenciaUbicacion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setSubmitting(true);
    setError(null);
    setResultado(null);
    try {
      const sugerencia = await sugerirUbicacion(token, {
        patio_id: patioId,
        contenedor_id: contenedorId,
        punto_referencia_ubicacion_id: puntoReferenciaId,
      });
      setResultado(sugerencia);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo calcular la sugerencia");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className={styles.main}>
      <h1>Sugerir ubicación</h1>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      {resultado && (
        <p className={styles.ok}>
          Sugerido: <span className="mono">{resultado.codigo}</span> (costo{" "}
          {resultado.costo.toFixed(2)})
        </p>
      )}
      <form className={styles.form} onSubmit={handleSubmit}>
        <label htmlFor="patio_id">ID de patio</label>
        <input id="patio_id" value={patioId} onChange={(e) => setPatioId(e.target.value)} required />

        <label htmlFor="contenedor_id">ID de contenedor</label>
        <input
          id="contenedor_id"
          value={contenedorId}
          onChange={(e) => setContenedorId(e.target.value)}
          required
        />

        <label htmlFor="punto_referencia_ubicacion_id">ID de ubicación de referencia</label>
        <input
          id="punto_referencia_ubicacion_id"
          value={puntoReferenciaId}
          onChange={(e) => setPuntoReferenciaId(e.target.value)}
          required
        />

        <button type="submit" disabled={submitting}>
          {submitting ? "Calculando..." : "Sugerir"}
        </button>
      </form>
    </main>
  );
}

export default function SugerirUbicacionPage() {
  return (
    <AuthGuard>
      <SugerirUbicacionContent />
    </AuthGuard>
  );
}
```

- [ ] **Step 9: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/ubicaciones/sugerir/page.test.tsx
```
Esperado: PASS (2 tests)

- [ ] **Step 10: Correr toda la suite de frontend**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test
```
Esperado: PASS — todos los tests de las Tasks 1-8.

- [ ] **Step 11: Correr el build de producción**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm run build
```
Esperado: build exitoso, sin errores de tipos.

- [ ] **Step 12: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/lib/api.ts frontend/lib/api.test.ts frontend/app/ubicaciones
git commit -m "feat: sugerencia de ubicacion por scoring"
```

---

## Self-Review

**Cobertura (spec sección 9, alcance confirmado — dashboard interno):**
- Login con paleta/logo de marca → Task 3.
- Navegación interna con logo, rol visible, logout → Task 4.
- CRUD de patios (crear admin, listar cualquier rol interno) → Task 5.
- Alta de contenedores + validación ISO 6346 (mensaje de error del backend) + detalle por ID → Task 6.
- Registro de movimientos (ingreso/reubicación/servicio/salida) → Task 7.
- Algoritmo de sugerencia de ubicación expuesto en UI → Task 8.
- Paleta de colores y tipografía (IBM Plex Sans/Mono) de la sección 9 → Tasks 1 y 4 (`globals.css`, fuentes vía `next/font/google`).
- Logo con restricción de fondo claro → Task 4 (colocado sobre `--surface` blanco en `NavBar`, nunca sobre `--azul`).

**Explícitamente fuera de alcance de este plan (confirmado con el usuario):** portal cliente (`solicitudes`), flujo QR/portería, PWA offline, mapa SVG con drag&drop, CRUD de usuarios/geocercas/admin, API de socios. Todo depende de endpoints de backend que no existen todavía.

**Placeholder scan:** sin "TBD"/"similar a Task N"/pasos sin código — cada step tiene el archivo completo.

**Consistencia de tipos:** `Patio`, `Contenedor`, `Movimiento`, `SugerenciaUbicacion` y sus campos coinciden exactamente entre `lib/api.ts` (Tasks 2, 5-8) y los schemas Pydantic reales (`PatioOut`, `ContenedorOut`, `MovimientoOut`, `SugerenciaUbicacionResponse` en `backend/app/schemas/*.py`). `AuthUser`/`useAuth()` definidos en Task 3 se usan con la misma forma (`user.rol`, `user.id`, `token`) en Tasks 4-8. `AuthGuard` (Task 4) envuelve el contenido de cada página protegida en Tasks 5-8 con el mismo patrón (`<AuthGuard><XxxContent /></AuthGuard>`).

**Limitación conocida (no es bug, es el estado real del backend):** no existe endpoint para listar contenedores por patio ni para listar ubicaciones disponibles — por eso los formularios de Tasks 6-8 piden IDs (UUID) escritos a mano en vez de selects poblados. Si se agregan esos endpoints al backend más adelante, un plan de seguimiento puede reemplazar esos inputs por selects/autocomplete.

---

**Plan guardado en `docs/superpowers/plans/2026-09-17-frontend-dashboard.md`.**
