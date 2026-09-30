"use client";

import type { ReportePreview } from "@/lib/api";
import { Button, DataTable, SkeletonText } from "@/components/ui";
import styles from "./TablaPreviewReporte.module.css";

interface TablaPreviewReporteProps {
  preview: ReportePreview | null;
  cargando?: boolean;
  onCambiarPagina: (page: number) => void;
}

interface FilaConIndice {
  indice: number;
  datos: Record<string, unknown>;
}

function formatearValor(valor: unknown): string {
  if (valor === null || valor === undefined) return "-";
  if (typeof valor === "boolean") return valor ? "Sí" : "No";
  return String(valor);
}

export function TablaPreviewReporte({
  preview,
  cargando = false,
  onCambiarPagina,
}: TablaPreviewReporteProps) {
  if (cargando) {
    return (
      <div className={styles.contenedor}>
        <SkeletonText lines={8} />
      </div>
    );
  }

  if (!preview) return null;

  const columnas = preview.columnas.map((columna) => ({
    key: columna.key,
    header: columna.label,
    // DataTable solo distingue inicio y fin. "center" del backend cae a inicio, que es la
    // alineación segura para texto; solo lo numérico se manda a la derecha.
    align: columna.align === "right" ? ("end" as const) : ("start" as const),
  }));

  const filas: FilaConIndice[] = preview.filas.map((datos, indice) => ({ indice, datos }));

  const primerRegistro =
    preview.total_registros === 0 ? 0 : (preview.page - 1) * preview.page_size + 1;
  const ultimoRegistro = Math.min(preview.page * preview.page_size, preview.total_registros);

  return (
    <div className={styles.contenedor}>
      <DataTable<FilaConIndice>
        columns={columnas}
        rows={filas}
        getRowKey={(fila) => String(fila.indice)}
        renderCell={(fila, key) => formatearValor(fila.datos[key])}
        caption={preview.titulo}
        emptyMessage="No hay registros para los filtros seleccionados."
      />

      <div className={styles.paginacion}>
        <p className={styles.conteo}>
          {primerRegistro}-{ultimoRegistro} de {preview.total_registros} registros
        </p>
        <div className={styles.controles}>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onCambiarPagina(preview.page - 1)}
            disabled={preview.page <= 1}
          >
            Anterior
          </Button>
          <span className={styles.pagina}>
            Página {preview.page} de {Math.max(preview.total_paginas, 1)}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onCambiarPagina(preview.page + 1)}
            disabled={preview.page >= preview.total_paginas}
          >
            Siguiente
          </Button>
        </div>
      </div>
    </div>
  );
}
