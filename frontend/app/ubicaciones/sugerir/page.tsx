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
