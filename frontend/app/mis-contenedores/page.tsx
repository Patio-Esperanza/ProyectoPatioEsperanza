"use client";

import { useEffect, useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import {
  ApiError,
  listPatios,
  listarContenedores,
  solicitarSalida,
  type Contenedor,
  type Patio,
} from "@/lib/api";
import styles from "./page.module.css";

function MisContenedoresContent() {
  const { token, user } = useAuth();
  const [contenedores, setContenedores] = useState<Contenedor[]>([]);
  const [patios, setPatios] = useState<Patio[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [abiertoId, setAbiertoId] = useState<string | null>(null);
  const [fecha, setFecha] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function cargar() {
    if (!token) return;
    setLoading(true);
    try {
      const [datosContenedores, datosPatios] = await Promise.all([
        listarContenedores(token),
        listPatios(token),
      ]);
      setContenedores(datosContenedores);
      setPatios(datosPatios);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar tus contenedores");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function handleSolicitar(id: string) {
    if (!token || !fecha) return;
    setSubmitting(true);
    setError(null);
    try {
      await solicitarSalida(token, id, fecha);
      setAbiertoId(null);
      setFecha("");
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo solicitar la salida");
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
      <h1>Mis contenedores</h1>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      {loading ? (
        <p>Cargando...</p>
      ) : (
        <ul className={styles.list}>
          {contenedores.map((c) => {
            const patio = patios.find((p) => p.id === c.patio_id);
            return (
              <li key={c.id}>
                <span className="mono">{c.numero_contenedor}</span> — estado {c.estado}
                {c.estado === "ubicado" && (
                  <>
                    <button onClick={() => setAbiertoId(c.id)}>Solicitar salida</button>
                    {abiertoId === c.id && (
                      <div className={styles.form}>
                        {patio && (
                          <p>Este patio requiere al menos {patio.anticipacion_minima_horas} horas de anticipación.</p>
                        )}
                        <label htmlFor={`fecha-${c.id}`}>Fecha y hora deseada</label>
                        <input
                          id={`fecha-${c.id}`}
                          type="datetime-local"
                          value={fecha}
                          onChange={(e) => setFecha(e.target.value)}
                        />
                        <button disabled={submitting} onClick={() => handleSolicitar(c.id)}>
                          {submitting ? "Enviando..." : "Confirmar solicitud"}
                        </button>
                      </div>
                    )}
                  </>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </main>
  );
}

export default function MisContenedoresPage() {
  return (
    <AuthGuard>
      <MisContenedoresContent />
    </AuthGuard>
  );
}
