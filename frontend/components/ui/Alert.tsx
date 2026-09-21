import type { ReactNode } from "react";
import styles from "./Alert.module.css";

interface AlertProps {
  tone: "info" | "success" | "warning" | "danger";
  children: ReactNode;
  titulo?: string;
}

/**
 * Cada tono lleva su propio icono. El color no puede ser el único indicador: quien no
 * distingue rojo de verde necesita la forma para saber si algo salió bien o mal.
 */
const ICONOS = {
  info: (
    <>
      <circle cx="10" cy="10" r="8" />
      <path d="M10 9v5M10 6v1" />
    </>
  ),
  success: (
    <>
      <circle cx="10" cy="10" r="8" />
      <path d="m6 10 3 3 5-6" />
    </>
  ),
  warning: (
    <>
      <path d="M10 2 19 18H1L10 2Z" />
      <path d="M10 8v4M10 14v1" />
    </>
  ),
  danger: (
    <>
      <circle cx="10" cy="10" r="8" />
      <path d="m7 7 6 6m0-6-6 6" />
    </>
  ),
};

export function Alert({ tone, children, titulo }: AlertProps) {
  return (
    <div
      className={`${styles.alerta} ${styles[tone]}`}
      // "alert" interrumpe al lector de pantalla; "status" espera a que termine lo que
      // está leyendo. Solo lo que exige atención inmediata merece interrumpir.
      role={tone === "danger" || tone === "warning" ? "alert" : "status"}
    >
      <svg
        className={styles.icono}
        width="20"
        height="20"
        viewBox="0 0 20 20"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        {ICONOS[tone]}
      </svg>
      <div className={styles.contenido}>
        {titulo && <p className={styles.titulo}>{titulo}</p>}
        <div>{children}</div>
      </div>
    </div>
  );
}
