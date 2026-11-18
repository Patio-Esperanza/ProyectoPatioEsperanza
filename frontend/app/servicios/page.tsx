"use client";

import { AuthGuard } from "@/components/AuthGuard";
import { ROLES_POR_RUTA } from "@/lib/rutas";
import { PanelCuadrilla } from "@/components/PanelCuadrilla";
import styles from "./page.module.css";

function ServiciosContent() {
  return (
    <main className={styles.main}>
      <h1>Servicios de hoy</h1>
      <PanelCuadrilla />
    </main>
  );
}

export default function ServiciosPage() {
  return (
    <AuthGuard roles={ROLES_POR_RUTA["/servicios"]}>
      <ServiciosContent />
    </AuthGuard>
  );
}
