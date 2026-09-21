"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { login, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import styles from "./page.module.css";

/**
 * Separa el fallo de red del fallo de credenciales. `fetch` lanza un `TypeError` cuando la
 * petición nunca sale (servidor caído, CORS, sin conexión); antes eso se mostraba con el
 * mismo texto genérico que una contraseña incorrecta, lo que hacía imposible distinguir
 * los dos casos al diagnosticar.
 */
function mensajeDeError(err: unknown): string {
  if (err instanceof ApiError) {
    return err.message;
  }
  if (err instanceof TypeError) {
    return "No se pudo contactar al servidor. Revisa tu conexión e inténtalo de nuevo.";
  }
  return "No se pudo iniciar sesión";
}

export default function LoginPage() {
  const router = useRouter();
  const { setToken } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const { access_token } = await login(email, password);
      setToken(access_token);
      router.push("/patios");
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className={styles.main}>
      <form className={styles.card} onSubmit={handleSubmit}>
        <h1>Patio Esperanza</h1>
        <label htmlFor="email">Correo</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <label htmlFor="password">Contraseña</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && (
          <p role="alert" className={styles.error}>
            {error}
          </p>
        )}
        <button type="submit" disabled={submitting}>
          {submitting ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </main>
  );
}
