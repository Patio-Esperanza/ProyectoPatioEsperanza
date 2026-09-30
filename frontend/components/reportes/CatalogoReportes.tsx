"use client";

import { useMemo, useState } from "react";
import type { ReporteTipo } from "@/lib/api";
import styles from "./CatalogoReportes.module.css";

export interface DefinicionReporte {
  tipo: ReporteTipo;
  titulo: string;
  descripcion: string;
}

/**
 * Catálogo fijo de los cinco reportes operativos. El backend valida el `tipo` contra su
 * propio enum, así que esta lista solo decide qué se ofrece en pantalla.
 */
export const REPORTES_DISPONIBLES: DefinicionReporte[] = [
  {
    tipo: "containers-in-yard",
    titulo: "Contenedores en Patio",
    descripcion: "Inventario actual de contenedores con su estadía acumulada.",
  },
  {
    tipo: "entry-movements",
    titulo: "Movimientos de Entrada",
    descripcion: "Ingresos registrados en el rango de fechas seleccionado.",
  },
  {
    tipo: "departure-movements",
    titulo: "Movimientos de Salida",
    descripcion: "Despachos y salidas confirmadas por portería.",
  },
  {
    tipo: "positions",
    titulo: "Reporte de Posiciones",
    descripcion: "Ocupación por carril, tramo, tira y nivel.",
  },
  {
    tipo: "special-services",
    titulo: "Servicios Especiales",
    descripcion: "Maniobras y servicios aplicados a contenedores.",
  },
];

interface CatalogoReportesProps {
  seleccionado: ReporteTipo;
  onSeleccionar: (tipo: ReporteTipo) => void;
  reportes?: DefinicionReporte[];
}

export function CatalogoReportes({
  seleccionado,
  onSeleccionar,
  reportes = REPORTES_DISPONIBLES,
}: CatalogoReportesProps) {
  const [busqueda, setBusqueda] = useState("");

  const filtrados = useMemo(() => {
    const termino = busqueda.trim().toLowerCase();
    if (!termino) return reportes;
    return reportes.filter(
      (reporte) =>
        reporte.titulo.toLowerCase().includes(termino) ||
        reporte.descripcion.toLowerCase().includes(termino)
    );
  }, [busqueda, reportes]);

  return (
    <nav className={styles.catalogo} aria-label="Catálogo de reportes">
      <div className={styles.buscador}>
        <label className="sr-only" htmlFor="buscador-reportes">
          Buscar reporte
        </label>
        <input
          id="buscador-reportes"
          type="search"
          className={styles.input}
          placeholder="Buscar reporte"
          value={busqueda}
          onChange={(evento) => setBusqueda(evento.target.value)}
        />
      </div>

      {filtrados.length === 0 ? (
        <p className={styles.vacio}>Ningún reporte coincide con la búsqueda.</p>
      ) : (
        <ul className={styles.lista}>
          {filtrados.map((reporte) => {
            const activo = reporte.tipo === seleccionado;
            return (
              <li key={reporte.tipo}>
                <button
                  type="button"
                  className={`${styles.item} ${activo ? styles.itemActivo : ""}`}
                  onClick={() => onSeleccionar(reporte.tipo)}
                  aria-current={activo ? "true" : undefined}
                >
                  <span className={styles.itemTitulo}>{reporte.titulo}</span>
                  <span className={styles.itemDescripcion}>{reporte.descripcion}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </nav>
  );
}
