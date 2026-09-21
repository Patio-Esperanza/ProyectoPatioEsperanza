"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { ROLES_POR_RUTA } from "@/lib/rutas";
import { useAuth } from "@/lib/auth-context";
import { ApiError, createCliente, listClientes, type Cliente, type TipoCliente } from "@/lib/api";
import styles from "./page.module.css";

const TIPOS: TipoCliente[] = [
  "agencia_aduanal",
  "importador_exportador",
  "transportista",
  "socio_api",
];

function ClientesContent() {
  const { token } = useAuth();
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [razonSocial, setRazonSocial] = useState("");
  const [rfc, setRfc] = useState("");
  const [tipo, setTipo] = useState<TipoCliente>("importador_exportador");
  const [creating, setCreating] = useState(false);

  const cargarClientes = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await listClientes(token);
      setClientes(data);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar los clientes");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    cargarClientes();
  }, [cargarClientes]);

  async function handleCrear(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setCreating(true);
    setError(null);
    try {
      await createCliente(token, { razon_social: razonSocial, rfc, tipo });
      setRazonSocial("");
      setRfc("");
      await cargarClientes();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el cliente");
    } finally {
      setCreating(false);
    }
  }


  return (
    <main className={styles.main}>
      <h1>Clientes</h1>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      {loading ? (
        <p>Cargando...</p>
      ) : (
        <ul className={styles.list}>
          {clientes.map((c) => (
            <li key={c.id}>
              <span className="mono">{c.rfc}</span> — {c.razon_social} — {c.tipo}
            </li>
          ))}
        </ul>
      )}

      <form className={styles.form} onSubmit={handleCrear}>
        <h2>Nuevo cliente</h2>
        <label htmlFor="razon_social">Razón social</label>
        <input
          id="razon_social"
          value={razonSocial}
          onChange={(e) => setRazonSocial(e.target.value)}
          required
        />
        <label htmlFor="rfc">RFC</label>
        <input id="rfc" value={rfc} onChange={(e) => setRfc(e.target.value)} required />
        <label htmlFor="tipo">Tipo</label>
        <select id="tipo" value={tipo} onChange={(e) => setTipo(e.target.value as TipoCliente)}>
          {TIPOS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <button type="submit" disabled={creating}>
          {creating ? "Creando..." : "Crear cliente"}
        </button>
      </form>
    </main>
  );
}

export default function ClientesPage() {
  return (
    <AuthGuard roles={ROLES_POR_RUTA["/clientes"]}>
      <ClientesContent />
    </AuthGuard>
  );
}
