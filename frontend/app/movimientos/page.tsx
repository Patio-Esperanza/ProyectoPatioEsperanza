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
