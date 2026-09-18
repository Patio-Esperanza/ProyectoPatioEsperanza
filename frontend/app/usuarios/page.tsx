"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import { ApiError, createUsuario, listUsuarios, type RolUsuario, type Usuario } from "@/lib/api";
import { usePatiosDisponibles } from "@/lib/use-patios-disponibles";
import styles from "./page.module.css";

const ROLES: RolUsuario[] = ["operador", "supervisor", "guardia", "despachador", "admin"];

function UsuariosContent() {
  const { token, user } = useAuth();
  const { patios: patiosDisponibles } = usePatiosDisponibles();
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tipo, setTipo] = useState<RolUsuario>("operador");
  const [patioIds, setPatioIds] = useState<string[]>([]);
  const [creating, setCreating] = useState(false);

  const cargarUsuarios = useCallback(async () => {
    if (!token || user?.rol !== "admin") return;
    setLoading(true);
    try {
      const data = await listUsuarios(token);
      setUsuarios(data);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar los usuarios");
    } finally {
      setLoading(false);
    }
  }, [token, user]);

  useEffect(() => {
    cargarUsuarios();
  }, [cargarUsuarios]);

  function togglePatio(id: string) {
    setPatioIds((prev) => (prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]));
  }

  async function handleCrear(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setCreating(true);
    setError(null);
    try {
      await createUsuario(token, { nombre, email, password, tipo, patio_ids: patioIds });
      setNombre("");
      setEmail("");
      setPassword("");
      setTipo("operador");
      setPatioIds([]);
      await cargarUsuarios();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el usuario");
    } finally {
      setCreating(false);
    }
  }

  if (user?.rol !== "admin") {
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
      <h1>Usuarios</h1>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      {loading ? (
        <p>Cargando...</p>
      ) : (
        <ul className={styles.list}>
          {usuarios.map((u) => (
            <li key={u.id}>
              <strong>{u.nombre}</strong> — {u.email} — <span className="mono">{u.tipo}</span> —{" "}
              {u.patios.map((p) => p.codigo).join(", ") || "sin patios"}
            </li>
          ))}
        </ul>
      )}

      <form className={styles.form} onSubmit={handleCrear}>
        <h2>Nuevo usuario</h2>
        <label htmlFor="nombre">Nombre</label>
        <input id="nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required />

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
          minLength={8}
        />

        <label htmlFor="tipo">Rol</label>
        <select id="tipo" value={tipo} onChange={(e) => setTipo(e.target.value as RolUsuario)}>
          {ROLES.map((rol) => (
            <option key={rol} value={rol}>
              {rol}
            </option>
          ))}
        </select>

        <fieldset>
          <legend>Patios asignados</legend>
          {patiosDisponibles.map((patio) => (
            <label key={patio.id}>
              <input
                type="checkbox"
                checked={patioIds.includes(patio.id)}
                onChange={() => togglePatio(patio.id)}
              />
              {patio.nombre} ({patio.codigo})
            </label>
          ))}
        </fieldset>

        <button type="submit" disabled={creating}>
          {creating ? "Creando..." : "Crear usuario"}
        </button>
      </form>
    </main>
  );
}

export default function UsuariosPage() {
  return (
    <AuthGuard>
      <UsuariosContent />
    </AuthGuard>
  );
}
