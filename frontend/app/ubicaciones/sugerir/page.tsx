"use client";

import { useState, type FormEvent } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { ROLES_POR_RUTA } from "@/lib/rutas";
import { PatioSelect } from "@/components/PatioSelect";
import { useAuth } from "@/lib/auth-context";
import { ApiError, sugerirUbicacion, type SugerenciaUbicacion } from "@/lib/api";
import styles from "./page.module.css";

function SugerirUbicacionContent() {
  const { token } = useAuth();
  const [patioId, setPatioId] = useState("");
  const [numeroContenedor, setNumeroContenedor] = useState("");
  const [puntoReferenciaCodigo, setPuntoReferenciaCodigo] = useState("");
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
        numero_contenedor: numeroContenedor,
        punto_referencia_codigo: puntoReferenciaCodigo,
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
        <label htmlFor="patio_id">Patio</label>
        <PatioSelect id="patio_id" value={patioId} onChange={setPatioId} />

        <label htmlFor="numero_contenedor">Número de contenedor</label>
        <input
          id="numero_contenedor"
          value={numeroContenedor}
          onChange={(e) => setNumeroContenedor(e.target.value)}
          required
        />

        <label htmlFor="punto_referencia_codigo">Código de ubicación de referencia</label>
        <input
          id="punto_referencia_codigo"
          value={puntoReferenciaCodigo}
          onChange={(e) => setPuntoReferenciaCodigo(e.target.value)}
          placeholder="A01-T01-R01-N1"
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
    <AuthGuard roles={ROLES_POR_RUTA["/ubicaciones/sugerir"]}>
      <SugerirUbicacionContent />
    </AuthGuard>
  );
}
