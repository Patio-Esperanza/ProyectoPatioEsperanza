"use client";

import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth-context";
import { Sidebar } from "./Sidebar";
import styles from "./AppShell.module.css";

/**
 * Envoltura de la aplicación. Sin sesión no dibuja nada alrededor: las páginas públicas
 * (login, registro, verificar) ocupan la pantalla completa.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const { user, ready } = useAuth();

  if (!ready || !user) {
    return <>{children}</>;
  }

  return (
    <div className={styles.shell}>
      <a href="#contenido" className={styles.saltar}>
        Saltar al contenido
      </a>
      <Sidebar />
      <div id="contenido" className={styles.contenido}>
        {children}
      </div>
    </div>
  );
}
