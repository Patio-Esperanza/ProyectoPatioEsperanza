"use client";

import { useState } from "react";
import type { DetalleTira as DetalleTiraData } from "@/lib/api";
import { Badge, Button, Field } from "@/components/ui";
import styles from "./DetalleTira.module.css";

function calcularDiasEnPatio(fechaIngreso: string): number {
  const ingreso = new Date(fechaIngreso);
  const ahora = new Date();
  const diff = ahora.getTime() - ingreso.getTime();
  return Math.floor(diff / (1000 * 60 * 60 * 24));
}

function calcularTonoDias(fechaIngreso: string): "success" | "warning" | "danger" {
  const dias = calcularDiasEnPatio(fechaIngreso);
  if (dias <= 7) return "success";
  if (dias <= 14) return "warning";
  return "danger";
}

interface DetalleTiraProps {
  detalle: DetalleTiraData;
  /** Id del contenedor pendiente elegido en el panel, o null si no hay ninguno. */
  contenedorSeleccionado: string | null;
  ubicacionSugeridaId: string | null;
  colocando: boolean;
  onColocar: (ubicacionId: string, motivo: string | null) => void;
}

export function DetalleTira({
  detalle,
  contenedorSeleccionado,
  ubicacionSugeridaId,
  colocando,
  onColocar,
}: DetalleTiraProps) {
  const [pidiendoMotivo, setPidiendoMotivo] = useState<string | null>(null);
  const [motivo, setMotivo] = useState("");

  function intentarColocar(ubicacionId: string) {
    if (ubicacionId === ubicacionSugeridaId) {
      onColocar(ubicacionId, null);
      return;
    }
    // Desviarse de la sugerencia queda registrado en el movimiento, y el motivo es lo que
    // hace util ese registro despues.
    setPidiendoMotivo(ubicacionId);
  }

  // Del nivel mas alto al mas bajo: asi se ve la pila en el patio.
  const nivelesDescendentes = [...detalle.niveles].sort((a, b) => b.nivel - a.nivel);

  return (
    <section className={styles.panel} aria-label={`Tira ${detalle.codigo}`}>
      <h2 className={styles.titulo}>{detalle.codigo}</h2>
      <ul className={styles.niveles}>
        {nivelesDescendentes.map((nivel) => (
          <li key={nivel.ubicacion_id} className={styles.nivel}>
            <span className={styles.etiquetaNivel}>N{nivel.nivel}</span>
            {nivel.contenedor ? (
              <span className={styles.datos}>
                <span className="mono">{nivel.contenedor.numero_contenedor}</span>
                <Badge tone="info">{nivel.contenedor.tamano} ft</Badge>
                <Badge tone={nivel.contenedor.tipo === "lleno" ? "warning" : "neutral"}>
                  {nivel.contenedor.tipo}
                </Badge>
                <Badge tone={calcularTonoDias(nivel.contenedor.fecha_ingreso)}>
                  {calcularDiasEnPatio(nivel.contenedor.fecha_ingreso)}d
                </Badge>
                <span className={styles.peso}>{nivel.contenedor.peso_kg} kg</span>
              </span>
            ) : (
              <span className={styles.datos}>
                <Badge tone={nivel.activo ? "success" : "neutral"}>
                  {nivel.activo ? "Libre" : "Inactiva"}
                </Badge>
                {nivel.ubicacion_id === ubicacionSugeridaId && <Badge tone="success">Sugerido</Badge>}
                {nivel.activo && contenedorSeleccionado && (
                  <Button
                    variant="secondary"
                    disabled={colocando}
                    onClick={() => intentarColocar(nivel.ubicacion_id)}
                  >
                    Colocar aquí
                  </Button>
                )}
              </span>
            )}
          </li>
        ))}
      </ul>

      {pidiendoMotivo && (
        <div className={styles.motivo}>
          <Field
            id="motivo-override"
            label="Motivo para no usar la ubicación sugerida"
            value={motivo}
            onChange={(event) => setMotivo(event.target.value)}
            required
          />
          <Button
            disabled={colocando || motivo.trim() === ""}
            onClick={() => {
              onColocar(pidiendoMotivo, motivo.trim());
              setPidiendoMotivo(null);
              setMotivo("");
            }}
          >
            Confirmar colocación
          </Button>
        </div>
      )}
    </section>
  );
}
