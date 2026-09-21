"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { ROLES_POR_RUTA } from "@/lib/rutas";
import { useAuth } from "@/lib/auth-context";
import { ApiError, actualizarPatio, createPatio, listPatios, type Patio } from "@/lib/api";
import styles from "./page.module.css";

function PatiosContent() {
  const { token, user } = useAuth();
  const [patios, setPatios] = useState<Patio[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nombre, setNombre] = useState("");
  const [codigo, setCodigo] = useState("");
  const [creating, setCreating] = useState(false);

  const cargarPatios = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await listPatios(token);
      setPatios(data);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar los patios");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    cargarPatios();
  }, [cargarPatios]);

  async function handleCrear(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setCreating(true);
    setError(null);
    try {
      await createPatio(token, { nombre, codigo });
      setNombre("");
      setCodigo("");
      await cargarPatios();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el patio");
    } finally {
      setCreating(false);
    }
  }

  async function handleActualizarAnticipacion(patioId: string, valor: number) {
    if (!token || Number.isNaN(valor) || valor <= 0) return;
    try {
      await actualizarPatio(token, patioId, valor);
      await cargarPatios();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar la anticipación");
    }
  }

  return (
    <main className={styles.main}>
      <h1>Patios</h1>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      {loading ? (
        <p>Cargando...</p>
      ) : (
        <ul className={styles.list}>
          {patios.map((patio) => (
            <li key={patio.id}>
              <span className="mono">{patio.codigo}</span> — {patio.nombre}
              {user?.rol === "admin" && (
                <span className={styles.anticipacion}>
                  <label htmlFor={`anticipacion-${patio.id}`}>
                    Anticipación mínima (h) — {patio.codigo}
                  </label>
                  <input
                    id={`anticipacion-${patio.id}`}
                    type="number"
                    min={1}
                    defaultValue={patio.anticipacion_minima_horas}
                    onBlur={(e) => handleActualizarAnticipacion(patio.id, Number(e.target.value))}
                  />
                </span>
              )}
            </li>
          ))}
        </ul>
      )}

      {user?.rol === "admin" && (
        <form className={styles.form} onSubmit={handleCrear}>
          <h2>Nuevo patio</h2>
          <label htmlFor="nombre">Nombre</label>
          <input id="nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
          <label htmlFor="codigo">Código</label>
          <input id="codigo" value={codigo} onChange={(e) => setCodigo(e.target.value)} required />
          <button type="submit" disabled={creating}>
            {creating ? "Creando..." : "Crear patio"}
          </button>
        </form>
      )}
    </main>
  );
}

export default function PatiosPage() {
  return (
    <AuthGuard roles={ROLES_POR_RUTA["/patios"]}>
      <PatiosContent />
    </AuthGuard>
  );
}
