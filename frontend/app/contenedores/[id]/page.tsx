"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import { ApiError, getContenedor, type Contenedor } from "@/lib/api";
import styles from "./page.module.css";

function ContenedorDetalleContent() {
  const params = useParams<{ id: string }>();
  const { token } = useAuth();
  const [contenedor, setContenedor] = useState<Contenedor | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    let cancelado = false;
    setLoading(true);
    getContenedor(token, params.id)
      .then((data) => {
        if (!cancelado) setContenedor(data);
      })
      .catch((err) => {
        if (!cancelado) {
          setError(err instanceof ApiError ? err.message : "No se pudo cargar el contenedor");
        }
      })
      .finally(() => {
        if (!cancelado) setLoading(false);
      });
    return () => {
      cancelado = true;
    };
  }, [token, params.id]);

  if (loading) return <p>Cargando...</p>;
  if (error)
    return (
      <p role="alert" className={styles.error}>
        {error}
      </p>
    );
  if (!contenedor) return null;

  return (
    <main className={styles.main}>
      <h1 className="mono">{contenedor.numero_contenedor}</h1>
      <dl className={styles.detalle}>
        <dt>Tipo</dt>
        <dd>{contenedor.tipo}</dd>
        <dt>Tamaño</dt>
        <dd>{contenedor.tamano}&apos;</dd>
        <dt>Estado</dt>
        <dd>{contenedor.estado}</dd>
        <dt>Peso</dt>
        <dd>{contenedor.peso_kg} kg</dd>
      </dl>
    </main>
  );
}

export default function ContenedorDetallePage() {
  return (
    <AuthGuard>
      <ContenedorDetalleContent />
    </AuthGuard>
  );
}
