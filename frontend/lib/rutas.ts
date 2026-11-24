/**
 * Mapa de rutas del frontend a los roles que pueden verlas.
 *
 * Se deriva de `require_roles` en el backend (`backend/app/api/routes/`). No inventa
 * permisos: donde el backend exige un rol para la acción principal de la página, aquí
 * aparece ese mismo rol. La excepción está documentada abajo.
 *
 * Esto es una capa de interfaz, no de seguridad. La autorización real vive en el backend.
 */

/** Los tres roles que el backend acepta para escribir (`_ROLES_ESCRITURA`). */
export const ROLES_STAFF = ["operador", "supervisor", "admin"] as const;

export const ROLES_POR_RUTA: Record<string, string[]> = {
  // `GET /api/patios` no exige rol, pero la página existe para administrar el patio y no
  // le sirve a un cliente. Restricción de interfaz, no de seguridad.
  "/patios": [...ROLES_STAFF],
  // `_ROLES_MAPA` y `POST /api/movimientos`.
  "/mapa": [...ROLES_STAFF],
  // `POST /api/contenedores` usa _ROLES_ESCRITURA.
  "/contenedores": [...ROLES_STAFF],
  // `POST /api/movimientos` usa _ROLES_ESCRITURA.
  "/movimientos": [...ROLES_STAFF],
  // `POST /api/ubicaciones/sugerir` usa _ROLES.
  "/ubicaciones/sugerir": [...ROLES_STAFF],
  // verificar-pin acepta `_ROLES_ESCRITURA` y `guardia` (Task 3).
  "/porteria": ["guardia", ...ROLES_STAFF],
  // GET /api/contenedores acepta cualquier sesión; RLS filtra por patio.
  "/salidas": ["despachador", ...ROLES_STAFF],
  // `_ROLES_GESTION_ORDEN` de `backend/app/api/servicios.py`.
  "/servicios": ["cuadrilla", "supervisor", "admin"],
  // `GET /api/reportes/...` usa require_roles(OPERADOR, SUPERVISOR, ADMIN, CLIENTE).
  "/reportes": [...ROLES_STAFF, "cliente"],
  // require_roles(RolUsuario.ADMIN).
  "/usuarios": ["admin"],
  "/clientes": ["admin"],
  // require_roles(RolUsuario.CLIENTE).
  "/solicitar": ["cliente"],
  "/mis-contenedores": ["cliente"],
};

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
