"use client";

import Link from "next/link";
import Image from "next/image";
import { useAuth } from "@/lib/auth-context";
import styles from "./NavBar.module.css";

export function NavBar() {
  const { user, logout } = useAuth();

  if (!user) {
    return null;
  }

  return (
    <nav className={styles.nav}>
      <Link href="/patios" className={styles.brand}>
        <Image src="/EsperanzaLogo.png" alt="Patio Esperanza" width={140} height={93} priority />
      </Link>
      <div className={styles.links}>
        <Link href="/patios">Patios</Link>
        <Link href="/contenedores">Contenedores</Link>
        <Link href="/movimientos">Movimientos</Link>
        <Link href="/ubicaciones/sugerir">Sugerir ubicación</Link>
        {user.rol === "admin" && <Link href="/usuarios">Usuarios</Link>}
        {user.rol === "cliente" && <Link href="/solicitar">Solicitar entrada</Link>}
      </div>
      <div className={styles.session}>
        <span className={styles.rol}>{user.rol}</span>
        <button onClick={logout}>Salir</button>
      </div>
    </nav>
  );
}
