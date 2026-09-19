"use client";

import { useEffect, useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import { ApiError, listarContenedores, type Contenedor } from "@/lib/api";
import styles from "./page.module.css";

function SalidasContent() {
  const { token, user } = useAuth();
  const [contenedores, setContenedores] = useState<Contenedor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelado = false;
    setLoading(true);
    listarContenedores(token, { estado: "solicitud_salida" })
      .then((data) => {
        if (!cancelado) setContenedores(data);
      })
      .catch((err) => {
        if (!cancelado) {
          setError(err instanceof ApiError ? err.message : "No se pudo cargar la cola de salidas");
        }
      })
      .finally(() => {
        if (!cancelado) setLoading(false);
      });
    return () => {
      cancelado = true;
    };
  }, [token]);

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
      <h1>Cola de salidas</h1>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      {loading ? (
        <p>Cargando...</p>
      ) : contenedores.length === 0 ? (
        <p>No hay solicitudes de salida pendientes.</p>
      ) : (
        <ul className={styles.list}>
          {contenedores.map((c) => (
            <li key={c.id}>
              <span className="mono">{c.numero_contenedor}</span> — salida deseada{" "}
              {c.fecha_deseada_salida
                ? new Date(c.fecha_deseada_salida).toLocaleString()
                : "sin fecha"}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

export default function SalidasPage() {
  return (
    <AuthGuard>
      <SalidasContent />
    </AuthGuard>
  );
}
