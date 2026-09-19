"use client";

import { useState, type FormEvent } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import { ApiError, verificarPin, type Contenedor } from "@/lib/api";
import styles from "./page.module.css";

function PorteriaContent() {
  const { token, user } = useAuth();
  const [numero, setNumero] = useState("");
  const [pin, setPin] = useState("");
  const [verificado, setVerificado] = useState<Contenedor | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setSubmitting(true);
    setError(null);
    setVerificado(null);
    try {
      const contenedor = await verificarPin(token, { numero_contenedor: numero, pin });
      setVerificado(contenedor);
      setNumero("");
      setPin("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo verificar el PIN");
    } finally {
      setSubmitting(false);
    }
  }

  if (user?.rol !== "operador" && user?.rol !== "supervisor" && user?.rol !== "admin") {
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
      <h1>Verificar PIN en portería</h1>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      {verificado && (
        <p className={styles.ok}>
          Contenedor <span className="mono">{verificado.numero_contenedor}</span> verificado —
          estado {verificado.estado}
        </p>
      )}
      <form className={styles.form} onSubmit={handleSubmit}>
        <label htmlFor="numero_contenedor">Número de contenedor</label>
        <input
          id="numero_contenedor"
          value={numero}
          onChange={(e) => setNumero(e.target.value)}
          required
          maxLength={11}
        />

        <label htmlFor="pin">PIN</label>
        <input
          id="pin"
          value={pin}
          onChange={(e) => setPin(e.target.value)}
          required
          maxLength={4}
          inputMode="numeric"
        />

        <button type="submit" disabled={submitting}>
          {submitting ? "Verificando..." : "Verificar"}
        </button>
      </form>
    </main>
  );
}

export default function PorteriaPage() {
  return (
    <AuthGuard>
      <PorteriaContent />
    </AuthGuard>
  );
}
