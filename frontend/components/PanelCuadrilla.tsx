"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import {
  ApiError,
  listarServicios,
  iniciarServicio,
  terminarServicio,
  type ServicioContenedor,
} from "@/lib/api";
import { Button, Card, Badge, Alert } from "@/components/ui";
import styles from "./PanelCuadrilla.module.css";

export function PanelCuadrilla() {
  const { token } = useAuth();
  const [servicios, setServicios] = useState<ServicioContenedor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [terminandoId, setTerminandoId] = useState<string | null>(null);
  const [notasTermino, setNotasTermino] = useState("");
  const [evidenciaUrl, setEvidenciaUrl] = useState("");

  const cargarServicios = async () => {
    if (!token) return;
    try {
      setLoading(true);
      const data = await listarServicios(token);
      setServicios(data);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar los servicios");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarServicios();
  }, [token]);

  const handleIniciar = async (id: string) => {
    if (!token) return;
    try {
      await iniciarServicio(token, id);
      await cargarServicios();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo iniciar el servicio");
    }
  };

  const handleTerminar = async (id: string, requiereEvidencia: boolean) => {
    if (!token) return;
    if (requiereEvidencia && !evidenciaUrl.trim()) {
      setError("Este servicio requiere evidencia fotográfica obligatoria");
      return;
    }
    try {
      await terminarServicio(token, id, {
        notas: notasTermino.trim() || undefined,
        evidencias: evidenciaUrl.trim() ? [evidenciaUrl.trim()] : undefined,
      });
      setTerminandoId(null);
      setNotasTermino("");
      setEvidenciaUrl("");
      await cargarServicios();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo terminar el servicio");
    }
  };

  if (loading) {
    return <p>Cargando servicios...</p>;
  }

  return (
    <div className={styles.container}>
      {error && <Alert variant="error">{error}</Alert>}
      {servicios.length === 0 ? (
        <p>No hay servicios registrados para hoy.</p>
      ) : (
        <div className={styles.grid}>
          {servicios.map((s) => {
            const requiereEvidencia = s.catalogo?.requiere_evidencia ?? false;
            return (
              <Card key={s.id} className={styles.card}>
                <div className={styles.header}>
                  <h3>{s.catalogo?.nombre ?? "Servicio"}</h3>
                  <Badge
                    tone={
                      s.estado === "terminado"
                        ? "success"
                        : s.estado === "en_proceso"
                        ? "info"
                        : s.estado === "programado"
                        ? "warning"
                        : "neutral"
                    }
                  >
                    {s.estado}
                  </Badge>
                </div>
                <p>
                  <strong>Contenedor ID:</strong> <span className="mono">{s.contenedor_id}</span>
                </p>
                {s.notas && (
                  <p>
                    <strong>Notas:</strong> {s.notas}
                  </p>
                )}
                {s.unidad_relacionada_ref && (
                  <p>
                    <strong>Segunda unidad:</strong> {s.unidad_relacionada_tipo} ({s.unidad_relacionada_ref})
                  </p>
                )}
                <div className={styles.actions}>
                  {(s.estado === "solicitado" || s.estado === "programado") && (
                    <Button onClick={() => handleIniciar(s.id)}>Iniciar</Button>
                  )}
                  {s.estado === "en_proceso" && (
                    <>
                      {terminandoId === s.id ? (
                        <div className={styles.terminarForm}>
                          <input
                            type="text"
                            placeholder="Notas opcionales"
                            value={notasTermino}
                            onChange={(e) => setNotasTermino(e.target.value)}
                            className={styles.input}
                          />
                          <input
                            type="text"
                            placeholder={requiereEvidencia ? "URL de evidencia (obligatoria)" : "URL de evidencia (opcional)"}
                            value={evidenciaUrl}
                            onChange={(e) => setEvidenciaUrl(e.target.value)}
                            className={styles.input}
                          />
                          <Button onClick={() => handleTerminar(s.id, requiereEvidencia)}>
                            Confirmar término
                          </Button>
                          <Button variant="outline" onClick={() => setTerminandoId(null)}>
                            Cancelar
                          </Button>
                        </div>
                      ) : (
                        <Button onClick={() => setTerminandoId(s.id)}>Terminar</Button>
                      )}
                    </>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
