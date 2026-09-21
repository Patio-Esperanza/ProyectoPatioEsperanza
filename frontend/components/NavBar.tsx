"use client";

import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import styles from "./NavBar.module.css";

export function NavBar() {
  const { user, logout } = useAuth();
  const router = useRouter();

  // `logout` solo limpia almacenamiento y estado. La navegación se hace aquí, explícita:
  // un contenedor de estado que navega por su cuenta esconde el efecto y es difícil de
  // probar.
  function handleLogout() {
    logout();
    router.replace("/login");
  }

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
        {(user.rol === "operador" || user.rol === "supervisor" || user.rol === "admin") && (
          <Link href="/porteria">Portería</Link>
        )}
        {(user.rol === "operador" || user.rol === "supervisor" || user.rol === "admin") && (
          <Link href="/salidas">Salidas</Link>
        )}
        {user.rol === "admin" && <Link href="/usuarios">Usuarios</Link>}
        {user.rol === "admin" && <Link href="/clientes">Clientes</Link>}
        {user.rol === "cliente" && <Link href="/solicitar">Solicitar entrada</Link>}
        {user.rol === "cliente" && <Link href="/mis-contenedores">Mis contenedores</Link>}
      </div>
      <div className={styles.session}>
        <span className={styles.rol}>{user.rol}</span>
        <button onClick={handleLogout}>Salir</button>
      </div>
    </nav>
  );
}
