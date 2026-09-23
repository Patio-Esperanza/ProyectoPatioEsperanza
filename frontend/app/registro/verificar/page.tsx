"use client";

import { useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { ApiError, verificarCliente } from "@/lib/api";
import styles from "../page.module.css";

export const dynamic = "force-static"; 

export default function VerificarPage() {
  const searchParams = useSearchParams();
  const emailInicial = searchParams.get("email") ?? "";
  const [email, setEmail] = useState(emailInicial);
  const [codigo, setCodigo] = useState("");
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMensaje(null);
    setSubmitting(true);
    try {
      const { detail } = await verificarCliente({ email, codigo });
      setMensaje(detail);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo verificar el código");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className={styles.main}>
      <form className={styles.card} onSubmit={handleSubmit}>
        <h1>Verifica tu correo</h1>
        <label htmlFor="email">Correo</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <label htmlFor="codigo">Código de 6 dígitos</label>
        <input
          id="codigo"
          value={codigo}
          onChange={(e) => setCodigo(e.target.value)}
          required
          maxLength={6}
        />
        {error && (
          <p role="alert" className={styles.error}>
            {error}
          </p>
        )}
        {mensaje && <p className={styles.ok}>{mensaje}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? "Verificando..." : "Verificar"}
        </button>
      </form>
    </main>
  );
}
