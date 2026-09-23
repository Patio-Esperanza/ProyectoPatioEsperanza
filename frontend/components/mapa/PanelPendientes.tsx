"use client";

import type { Contenedor } from "@/lib/api";
import { EmptyState, SkeletonText } from "@/components/ui";
import styles from "./PanelPendientes.module.css";

interface PanelPendientesProps {
  contenedores: Contenedor[];
  seleccionadoId: string | null;
  cargando: boolean;
  onSeleccionar: (contenedorId: string) => void;
}

export function PanelPendientes({
  contenedores,
  seleccionadoId,
  cargando,
  onSeleccionar,
}: PanelPendientesProps) {
  return (
    <section className={styles.panel} aria-label="Contenedores por ubicar">
      <h2 className={styles.titulo}>Por ubicar</h2>
      {cargando && <SkeletonText lines={3} />}
      {!cargando && contenedores.length === 0 && (
        <EmptyState titulo="No hay contenedores por ubicar" />
      )}
      {!cargando && contenedores.length > 0 && (
        <ul className={styles.lista}>
          {contenedores.map((contenedor) => (
            <li key={contenedor.id}>
              <button
                type="button"
                aria-pressed={contenedor.id === seleccionadoId}
                className={styles.item}
                onClick={() => onSeleccionar(contenedor.id)}
              >
                <span className="mono">{contenedor.numero_contenedor}</span>
                <span className={styles.meta}>
                  {contenedor.tamano} ft · {contenedor.tipo} · {contenedor.peso_kg} kg
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
