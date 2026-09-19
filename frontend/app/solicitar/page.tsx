"use client";

import { useState, type FormEvent } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import {
  ApiError,
  solicitarContenedor,
  type Contenedor,
  type TamanoContenedor,
  type TipoContenedor,
} from "@/lib/api";
import styles from "./page.module.css";

function SolicitarContent() {
  const { token, user } = useAuth();
  const [numero, setNumero] = useState("");
  const [tipo, setTipo] = useState<TipoContenedor>("lleno");
  const [tamano, setTamano] = useState<TamanoContenedor>("40");
  const [pesoKg, setPesoKg] = useState("");
  const [fechaEstimadaRetiro, setFechaEstimadaRetiro] = useState("");
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
      const contenedor = await solicitarContenedor(token, {
        numero_contenedor: numero,
        tipo,
        tamano,
        peso_kg: Number(pesoKg),
        fecha_estimada_retiro: fechaEstimadaRetiro || undefined,
      });
      setCreado(contenedor);
      setNumero("");
      setPesoKg("");
      setFechaEstimadaRetiro("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo enviar la solicitud");
    } finally {
      setSubmitting(false);
    }
  }

  if (user?.rol !== "cliente") {
    return (
      <main className={styles.main}>
        <p role="alert" className={styles.error}>
          No autorizado para ver esta página
        </p>
      </main>
    );
  }

  return (
    <main className={styles.main}>
      <h1>Solicitar entrada de contenedor</h1>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      {creado && (
        <p className={styles.ok}>
          Solicitud registrada: <span className="mono">{creado.numero_contenedor}</span> — estado{" "}
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

        <label htmlFor="peso_kg">Peso (kg)</label>
        <input
          id="peso_kg"
          type="number"
          value={pesoKg}
          onChange={(e) => setPesoKg(e.target.value)}
          required
        />

        <label htmlFor="fecha_estimada_retiro">Fecha posible de retiro</label>
        <input
          id="fecha_estimada_retiro"
          type="date"
          value={fechaEstimadaRetiro}
          onChange={(e) => setFechaEstimadaRetiro(e.target.value)}
        />

        <button type="submit" disabled={submitting}>
          {submitting ? "Enviando..." : "Enviar solicitud"}
        </button>
      </form>
    </main>
  );
}

export default function SolicitarPage() {
  return (
    <AuthGuard>
      <SolicitarContent />
    </AuthGuard>
  );
}
