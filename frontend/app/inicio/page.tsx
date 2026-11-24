"use client";

import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import { EmptyState } from "@/components/ui";
import styles from "./page.module.css";

function InicioContent() {
  const { user } = useAuth();
  const rol = user?.rol ?? "desconocido";

  return (
    <main className={styles.main}>
      <EmptyState
        titulo="Tu rol aún no tiene pantalla de trabajo"
        descripcion={`Rol: ${rol}. Pídele a un supervisor lo que necesites mientras la habilitamos.`}
      />
    </main>
  );
}

export default function InicioPage() {
  return (
    <AuthGuard>
      <InicioContent />
    </AuthGuard>
  );
}
