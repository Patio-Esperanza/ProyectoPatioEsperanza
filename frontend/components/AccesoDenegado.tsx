"use client";

import Link from "next/link";
import { homePorRol } from "@/lib/rutas";
import styles from "./AccesoDenegado.module.css";

export function AccesoDenegado({ rol }: { rol: string }) {
  return (
    <main className={styles.main}>
      <div className={styles.card}>
        <h1 className={styles.titulo}>No tienes permiso para ver esta página</h1>
        <p className={styles.texto}>
          Tu sesión tiene el rol <span className={styles.rol}>{rol}</span>, que no puede
          entrar a esta sección. Si crees que es un error, pídele acceso a un
          administrador.
        </p>
        <Link href={homePorRol(rol)} className={styles.accion}>
          Ir al inicio
        </Link>
      </div>
    </main>
  );
}
