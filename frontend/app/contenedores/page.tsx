"use client";

import { useState, type FormEvent } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { PatioSelect } from "@/components/PatioSelect";
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

        <label htmlFor="patio_id">Patio</label>
        <PatioSelect id="patio_id" value={patioId} onChange={setPatioId} />

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
