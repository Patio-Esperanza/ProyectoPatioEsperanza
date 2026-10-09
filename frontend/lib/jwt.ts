export interface JwtPayload {
  sub: string;
  rol: string;
  patios: string[];
  iat: number;
  exp: number;
  cliente_id?: string;
}

export function decodeJwtPayload(token: string): JwtPayload {
  const base64Url = token.split(".")[1];
  const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
  const json = atob(base64);
  return JSON.parse(json) as JwtPayload;
}

/**
 * Versión que nunca lanza. Un token corrupto en localStorage (recorte, edición manual,
 * cambio de formato) reventaba el render del AuthProvider y dejaba la app en blanco sin
 * forma de recuperarse; aquí se trata como "sin sesión" y el usuario vuelve al login.
 */
export function decodeTokenSafe(token: string): JwtPayload | null {
  try {
    if (token.split(".").length !== 3) return null;
    const payload = decodeJwtPayload(token);
    if (
      !payload ||
      typeof payload.sub !== "string" ||
      !payload.sub ||
      typeof payload.rol !== "string" ||
      !Array.isArray(payload.patios) ||
      !payload.patios.every((patio) => typeof patio === "string") ||
      !Number.isFinite(payload.iat) ||
      !Number.isFinite(payload.exp) ||
      (payload.cliente_id !== undefined && typeof payload.cliente_id !== "string")
    ) {
      return null;
    }
    return payload;
  } catch {
    return null;
  }
}

export function tokenCaducado(payload: JwtPayload): boolean {
  return payload.exp < Date.now() / 1000;
}

/** Segundos que faltan para que caduque. Negativo si ya caducó. */
export function tiempoHastaExpiracion(payload: JwtPayload): number {
  return payload.exp - Date.now() / 1000;
}
