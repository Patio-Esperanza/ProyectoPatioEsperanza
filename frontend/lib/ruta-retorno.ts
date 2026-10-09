const CLAVE = "patio_esperanza_ruta_retorno";

/**
 * Solo se acepta una ruta interna. Un valor como `//evil.com` o `https://evil.com` lo lee
 * el navegador como destino externo, así que guardar lo que venga en la URL permitiría
 * mandar al usuario fuera del sitio justo después de que escribió su contraseña.
 */
export function rutaSegura(ruta: string | null | undefined): string | null {
  if (!ruta) return null;
  if (!ruta.startsWith("/")) return null;
  if (ruta.startsWith("//")) return null;
  if (ruta.includes("\\")) return null;
  // eslint-disable-next-line no-control-regex
  if (/[\u0000-\u001f\u007f]/.test(ruta)) return null;
  if (ruta === "/login" || ruta.startsWith("/login?")) return null;
  return ruta;
}

/** Recuerda dónde estaba el usuario para devolverlo ahí después del login. */
export function guardarRutaRetorno(ruta: string): void {
  const valida = rutaSegura(ruta);
  if (!valida) return;
  try {
    sessionStorage.setItem(CLAVE, valida);
  } catch {
    // Modo privado o almacenamiento lleno: se pierde el retorno, no la sesión.
  }
}

/** Devuelve la ruta guardada y la consume, para que no reaparezca en el siguiente login. */
export function tomarRutaRetorno(): string | null {
  try {
    const guardada = sessionStorage.getItem(CLAVE);
    sessionStorage.removeItem(CLAVE);
    return rutaSegura(guardada);
  } catch {
    return null;
  }
}
