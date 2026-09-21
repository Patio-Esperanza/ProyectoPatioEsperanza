"use client";

import { useState, type FormEvent } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { login, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Alert, Button, Field } from "@/components/ui";
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
        <div className={styles.marca}>
          <Image
            src="/EsperanzaLogo.png"
            alt="Patio Esperanza"
            width={160}
            height={107}
            priority
          />
        </div>

        <div className={styles.encabezado}>
          <h1 className={styles.titulo}>Iniciar sesión</h1>
          <p className={styles.subtitulo}>Gestión de patio de contenedores</p>
        </div>

        {error && <Alert tone="danger">{error}</Alert>}

        <Field
          label="Correo"
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          // Deja que el gestor de contraseñas del navegador rellene la pareja.
          autoComplete="username"
        />

        <Field
          label="Contraseña"
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
        />

        <Button type="submit" loading={submitting} className={styles.enviar}>
          Entrar
        </Button>
      </form>
    </main>
  );
}
