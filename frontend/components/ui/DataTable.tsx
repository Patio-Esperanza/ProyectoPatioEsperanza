import type { ReactNode } from "react";
import styles from "./DataTable.module.css";

interface DataTableProps<T> {
  columns: Array<{ key: string; header: string; align?: "start" | "end"; mono?: boolean }>;
  rows: T[];
  getRowKey: (row: T) => string;
  renderCell: (row: T, key: string) => ReactNode;
  caption?: string;
  emptyMessage?: string;
}

export function DataTable<T>({
  columns,
  rows,
  getRowKey,
  renderCell,
  caption,
  emptyMessage = "No hay registros para mostrar.",
}: DataTableProps<T>) {
  return (
    <div className={styles.contenedor}>
      <table className={styles.tabla}>
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                className={`${styles[column.align ?? "start"]} ${column.mono ? "mono" : ""}`}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              {/* colSpan mínimo 1: un colSpan de 0 hace que la celda abarque hasta el
                  final de la fila en unos navegadores y nada en otros. */}
              <td colSpan={Math.max(columns.length, 1)} className={styles.vacio}>
                {emptyMessage}
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr key={getRowKey(row)}>
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={`${styles[column.align ?? "start"]} ${
                      column.mono ? "mono" : ""
                    }`}
                  >
                    {renderCell(row, column.key)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
