import type { ReactNode } from "react";
import styles from "./PageHeader.module.css";

interface PageHeaderProps {
  titulo: string;
  descripcion?: string;
  accion?: ReactNode;
}

export function PageHeader({ titulo, descripcion, accion }: PageHeaderProps) {
  return (
    <header className={styles.cabecera}>
      <div className={styles.contenido}>
        <h1 className={styles.titulo}>{titulo}</h1>
        {descripcion && <p className={styles.descripcion}>{descripcion}</p>}
      </div>
      {accion && <div className={styles.accion}>{accion}</div>}
    </header>
  );
}
