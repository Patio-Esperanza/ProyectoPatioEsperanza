"use client";

import type { FiltrosReportePayload, Patio } from "@/lib/api";
import { Button, Field } from "@/components/ui";
import styles from "./FiltrosReporteBar.module.css";

export interface FiltrosReporteBarProps {
  filtros: FiltrosReportePayload;
  patios: Patio[];
  onCambiar: (filtros: FiltrosReportePayload) => void;
  onDescargar: () => void;
  onProgramar: () => void;
  descargando?: boolean;
  deshabilitado?: boolean;
}

export function FiltrosReporteBar({
  filtros,
  patios,
  onCambiar,
  onDescargar,
  onProgramar,
  descargando = false,
  deshabilitado = false,
}: FiltrosReporteBarProps) {
  // Cualquier cambio de filtro regresa a la página 1: mantener la página anterior deja al
  // usuario en una página que con el filtro nuevo puede ya no existir.
  function actualizar(cambio: Partial<FiltrosReportePayload>) {
    onCambiar({ ...filtros, ...cambio, page: 1 });
  }

  return (
    <section className={styles.barra} aria-label="Filtros del reporte">
      <div className={styles.campos}>
        <Field
          id="filtro-fecha-inicio"
          label="Desde"
          type="date"
          value={filtros.fecha_inicio ?? ""}
          onChange={(evento) => actualizar({ fecha_inicio: evento.target.value || undefined })}
        />
        <Field
          id="filtro-fecha-fin"
          label="Hasta"
          type="date"
          value={filtros.fecha_fin ?? ""}
          onChange={(evento) => actualizar({ fecha_fin: evento.target.value || undefined })}
        />

        <div className={styles.campo}>
          <label className={styles.etiqueta} htmlFor="filtro-patio">
            Patio
          </label>
          <select
            id="filtro-patio"
            className={styles.select}
            value={filtros.patio_id ?? ""}
            onChange={(evento) => actualizar({ patio_id: evento.target.value || undefined })}
          >
            <option value="">Todos</option>
            {patios.map((patio) => (
              <option key={patio.id} value={patio.id}>
                {patio.nombre}
              </option>
            ))}
          </select>
        </div>

        <Field
          id="filtro-busqueda"
          label="Buscar"
          type="search"
          placeholder="Contenedor, cliente..."
          value={filtros.busqueda ?? ""}
          onChange={(evento) => actualizar({ busqueda: evento.target.value || undefined })}
        />
      </div>

      <div className={styles.acciones}>
        <Button
          variant="secondary"
          onClick={onProgramar}
          disabled={deshabilitado}
        >
          Programar envío
        </Button>
        <Button onClick={onDescargar} loading={descargando} disabled={deshabilitado}>
          Descargar Excel
        </Button>
      </div>
    </section>
  );
}
