"use client";

import type { ReporteProgramado } from "@/lib/api";
import { Badge, Button, EmptyState, SkeletonText } from "@/components/ui";
import styles from "./PanelReportesProgramados.module.css";

interface PanelReportesProgramadosProps {
  programados: ReporteProgramado[];
  cargando?: boolean;
  ocupadoId?: string | null;
  onProbar: (id: string) => void;
  onAlternarActivo: (programado: ReporteProgramado) => void;
  onEliminar: (id: string) => void;
}

const DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

function describirHorario(programado: ReporteProgramado): string {
  const reloj = `${String(programado.hora).padStart(2, "0")}:${String(
    programado.minuto
  ).padStart(2, "0")}`;

  if (programado.frecuencia === "semanal") {
    const dia = DIAS_SEMANA[programado.dia_semana ?? 0] ?? DIAS_SEMANA[0];
    return `Cada ${dia} a las ${reloj}`;
  }
  if (programado.frecuencia === "mensual") {
    return `Día ${programado.dia_mes ?? 1} de cada mes a las ${reloj}`;
  }
  return `Todos los días a las ${reloj}`;
}

function tonoEstado(estado: string | null): "neutral" | "success" | "danger" {
  if (estado === "enviado") return "success";
  if (estado === "error") return "danger";
  return "neutral";
}

export function PanelReportesProgramados({
  programados,
  cargando = false,
  ocupadoId = null,
  onProbar,
  onAlternarActivo,
  onEliminar,
}: PanelReportesProgramadosProps) {
  if (cargando) {
    return (
      <section className={styles.panel} aria-label="Envíos automáticos">
        <SkeletonText lines={4} />
      </section>
    );
  }

  return (
    <section className={styles.panel} aria-label="Envíos automáticos">
      <h2 className={styles.titulo}>Envíos automáticos</h2>

      {programados.length === 0 ? (
        <EmptyState
          titulo="Sin envíos programados"
          descripcion="Usa Programar envío para mandar este reporte por correo de forma periódica."
        />
      ) : (
        <ul className={styles.lista}>
          {programados.map((programado) => {
            const ocupado = ocupadoId === programado.id;
            return (
              <li key={programado.id} className={styles.item}>
                <div className={styles.encabezadoItem}>
                  <span className={styles.nombre}>{programado.nombre}</span>
                  <Badge tone={programado.activo ? "success" : "neutral"}>
                    {programado.activo ? "Activo" : "Pausado"}
                  </Badge>
                </div>

                <p className={styles.detalle}>{describirHorario(programado)}</p>
                <p className={styles.detalle}>
                  {programado.destinatarios.join(", ")}
                </p>

                {programado.ultimo_estado && (
                  <p className={styles.detalle}>
                    Último envío:{" "}
                    <Badge tone={tonoEstado(programado.ultimo_estado)}>
                      {programado.ultimo_estado}
                    </Badge>
                    {programado.ultimo_error && (
                      <span className={styles.error}> {programado.ultimo_error}</span>
                    )}
                  </p>
                )}

                <div className={styles.acciones}>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => onProbar(programado.id)}
                    loading={ocupado}
                  >
                    Probar envío
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onAlternarActivo(programado)}
                    disabled={ocupado}
                  >
                    {programado.activo ? "Pausar" : "Reanudar"}
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => onEliminar(programado.id)}
                    disabled={ocupado}
                  >
                    Eliminar
                  </Button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
