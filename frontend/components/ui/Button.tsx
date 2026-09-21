"use client";

import type { ButtonHTMLAttributes } from "react";
import styles from "./Button.module.css";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md";
  loading?: boolean;
}

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  children,
  className,
  // Por defecto "button": un <button> sin type dentro de un <form> envía el formulario,
  // que casi nunca es lo que se quiere de un botón suelto.
  type = "button",
  "aria-busy": ariaBusy,
  ...props
}: ButtonProps) {
  return (
    <button
      {...props}
      type={type}
      className={`${styles.boton} ${styles[variant]} ${styles[size]} ${className ?? ""}`}
      disabled={disabled || loading}
      aria-busy={loading ? true : ariaBusy}
    >
      {loading && (
        <svg
          className={styles.spinner}
          width="20"
          height="20"
          viewBox="0 0 20 20"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
          aria-hidden="true"
        >
          <path d="M10 2a8 8 0 1 1-8 8" strokeLinecap="round" />
        </svg>
      )}
      {children}
    </button>
  );
}
