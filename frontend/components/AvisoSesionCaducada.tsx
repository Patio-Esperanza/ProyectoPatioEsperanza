"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { Alert, Button, Card } from "./ui";

export function AvisoSesionCaducada() {
  const { tokenExpiresAt, proximaExpiracion, errorRefresh, renovarSesion, logout } = useAuth();
  const [segundos, setSegundos] = useState(120);
  const [renovando, setRenovando] = useState(false);
  useEffect(() => {
    if (!proximaExpiracion || tokenExpiresAt === null) return;
    const actualizar = () => setSegundos(Math.max(0, Math.min(120, Math.ceil((tokenExpiresAt - Date.now()) / 1000))));
    actualizar();
    const timer = setInterval(actualizar, 1000);
    return () => clearInterval(timer);
  }, [proximaExpiracion, tokenExpiresAt]);

  if (!proximaExpiracion) return null;
  async function renovar() {
    setRenovando(true);
    try { await renovarSesion(); } catch { /* El contexto muestra el error. */ }
    finally { setRenovando(false); }
  }
  return (
    <section aria-labelledby="aviso-sesion-titulo" style={{
      position: "fixed", right: "var(--space-4)", bottom: "var(--space-4)",
      zIndex: "var(--z-toast)", width: "min(440px, calc(100vw - 32px))",
      maxHeight: "calc(100dvh - 32px)", overflowY: "auto", boxShadow: "var(--shadow-3)",
    }}>
      <Card>
        <h2 id="aviso-sesion-titulo" style={{ fontSize: "var(--text-lg)" }}>Tu sesion expira en 2 minutos</h2>
        <p>{segundos > 0 ? `Tiempo restante: ${segundos} s` : "Tu sesión ha caducado."}</p>
        {errorRefresh ? <Alert tone="danger">No se pudo renovar la sesión automáticamente. Intenta renovarla de nuevo.</Alert> :
          <p>Renovaremos tu sesión automáticamente para que puedas continuar.</p>}
        <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-3)", marginTop: "var(--space-4)" }}>
          <Button loading={renovando} onClick={renovar}>Renovar sesion</Button>
          <Button variant="secondary" onClick={logout}>Cerrar sesion</Button>
        </div>
      </Card>
    </section>
  );
}
