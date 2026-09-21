"use client";

import type { InputHTMLAttributes } from "react";
import styles from "./Field.module.css";

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  id: string;
  error?: string;
  hint?: string;
  required?: boolean;
  /**
   * Oculta la etiqueta a la vista sin quitarla del árbol de accesibilidad. Solo para
   * cuando algo cercano ya la muestra, como el encabezado de una columna con un campo por
   * fila. Nunca para ahorrar espacio: un campo sin etiqueta visible no se entiende.
   */
  labelHidden?: boolean;
}

export function Field({
  label,
  id,
  error,
  hint,
  required,
  labelHidden = false,
  className,
  "aria-describedby": describedBy,
  "aria-invalid": ariaInvalid,
  ...props
}: FieldProps) {
  // El error tiene prioridad sobre la ayuda: cuando hay error, la ayuda deja de mostrarse
  // y de anunciarse, para no competir con el mensaje que el usuario necesita leer ahora.
  const mensajeId = error ? `${id}-error` : hint ? `${id}-hint` : undefined;
  const descripcion = [describedBy, mensajeId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={styles.campo}>
      <div className={labelHidden ? "sr-only" : styles.filaEtiqueta}>
        <label className={styles.etiqueta} htmlFor={id}>
          {label}
        </label>
        {/*
         * El asterisco vive fuera del <label> y es decorativo. Meterlo dentro ensucia el
         * nombre accesible del campo ("Correo *") sin aportar nada: el atributo required
         * del input ya le dice a la tecnología asistiva que es obligatorio.
         */}
        {required && (
          <span className={styles.obligatorio} aria-hidden="true">
            *
          </span>
        )}
      </div>
      <input
        {...props}
        id={id}
        required={required}
        className={`${styles.input} ${className ?? ""}`}
        aria-describedby={descripcion}
        aria-invalid={error ? true : ariaInvalid}
      />
      {error ? (
        <p id={mensajeId} className={styles.error} role="alert">
          {error}
        </p>
      ) : hint ? (
        <p id={mensajeId} className={styles.ayuda}>
          {hint}
        </p>
      ) : null}
    </div>
  );
}
