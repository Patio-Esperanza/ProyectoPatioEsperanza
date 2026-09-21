"use client";

import type { InputHTMLAttributes } from "react";
import styles from "./Field.module.css";

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  id: string;
  error?: string;
  hint?: string;
  required?: boolean;
}

export function Field({
  label,
  id,
  error,
  hint,
  required,
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
      <label className={styles.etiqueta} htmlFor={id}>
        {label}
        {required && (
          <>
            {" "}
            <span aria-hidden="true">*</span>
            <span className="sr-only">(obligatorio)</span>
          </>
        )}
      </label>
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
