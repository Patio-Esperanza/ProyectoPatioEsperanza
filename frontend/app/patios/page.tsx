"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import { ApiError, createPatio, listPatios, type Patio } from "@/lib/api";
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
    <AuthGuard>
      <PatiosContent />
    </AuthGuard>
  );
}
