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
  // `GET /api/patios/{id}/mapa` usa los mismos roles que _ROLES_ESCRITURA.
  "/mapa": [...ROLES_STAFF],
  // `POST /api/contenedores` usa _ROLES_ESCRITURA.
  "/contenedores": [...ROLES_STAFF],
  // `POST /api/movimientos` usa _ROLES_ESCRITURA.
  "/movimientos": [...ROLES_STAFF],
  // `POST /api/ubicaciones/sugerir` usa _ROLES.
  "/ubicaciones/sugerir": [...ROLES_STAFF],
  // `POST /api/contenedores/verificar-pin` usa _ROLES_ESCRITURA.
  "/porteria": [...ROLES_STAFF],
  // Cola de planeación, consume `GET /api/contenedores` con scoping de staff.
  "/salidas": [...ROLES_STAFF],
  // require_roles(RolUsuario.ADMIN).
  "/usuarios": ["admin"],
  "/clientes": ["admin"],
  // require_roles(RolUsuario.CLIENTE).
  "/solicitar": ["cliente"],
  "/mis-contenedores": ["cliente"],
};

/**
 * Ruta de inicio de cada rol. La usan la pantalla de acceso denegado, la raíz `/` y el
 * destino después de iniciar sesión.
 */
export function homePorRol(rol: string): string {
  return rol === "cliente" ? "/mis-contenedores" : "/patios";
}
