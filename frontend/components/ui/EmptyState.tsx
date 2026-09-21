import type { ReactNode } from "react";
import styles from "./EmptyState.module.css";

interface EmptyStateProps {
  titulo: string;
  descripcion?: string;
  accion?: ReactNode;
}

export function EmptyState({ titulo, descripcion, accion }: EmptyStateProps) {
  return (
    <div className={styles.estado}>
      <h2 className={styles.titulo}>{titulo}</h2>
      {descripcion && <p className={styles.descripcion}>{descripcion}</p>}
      {accion && <div className={styles.accion}>{accion}</div>}
    </div>
  );
}
