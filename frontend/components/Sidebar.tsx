"use client";

import { useEffect, useId, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { ROLES_POR_RUTA } from "@/lib/rutas";
import styles from "./Sidebar.module.css";

interface Enlace {
  href: string;
  texto: string;
}

interface Seccion {
  titulo: string;
  enlaces: Enlace[];
}

/**
 * Las secciones completas. Cada enlace se filtra contra ROLES_POR_RUTA, que es la misma
 * fuente que usa AuthGuard: si una ruta cambia de roles, el menú y el guard se mueven
 * juntos y no pueden quedar desalineados.
 */
const SECCIONES: Seccion[] = [
  {
    titulo: "Operación",
    enlaces: [
      { href: "/contenedores", texto: "Contenedores" },
      { href: "/movimientos", texto: "Movimientos" },
      { href: "/ubicaciones/sugerir", texto: "Sugerir ubicación" },
      { href: "/porteria", texto: "Portería" },
      { href: "/salidas", texto: "Salidas" },
    ],
  },
  {
    titulo: "Administración",
    enlaces: [
      { href: "/patios", texto: "Patios" },
      { href: "/usuarios", texto: "Usuarios" },
      { href: "/clientes", texto: "Clientes" },
    ],
  },
  {
    titulo: "Cliente",
    enlaces: [
      { href: "/mis-contenedores", texto: "Mis contenedores" },
      { href: "/solicitar", texto: "Solicitar entrada" },
    ],
  },
];

function puedeVer(href: string, rol: string): boolean {
  const permitidos = ROLES_POR_RUTA[href];
  // Sin entrada en el mapa, la ruta la ve cualquier sesión.
  return permitidos ? permitidos.includes(rol) : true;
}

export function Sidebar() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [abierto, setAbierto] = useState(false);
  const navId = useId();

  // Al navegar, el drawer se cierra solo. Dejarlo abierto encima de la página nueva es
  // desorientador en móvil.
  useEffect(() => {
    setAbierto(false);
  }, [pathname]);

  if (!user) {
    return null;
  }

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  const secciones = SECCIONES.map((seccion) => ({
    ...seccion,
    enlaces: seccion.enlaces.filter((enlace) => puedeVer(enlace.href, user.rol)),
  })).filter((seccion) => seccion.enlaces.length > 0);

  return (
    <>
      <button
        type="button"
        className={styles.disparador}
        aria-expanded={abierto}
        aria-controls={navId}
        onClick={() => setAbierto((v) => !v)}
      >
        <span aria-hidden="true">{abierto ? "✕" : "☰"}</span>
        <span className="sr-only">{abierto ? "Cerrar menú" : "Abrir menú"}</span>
      </button>

      {abierto && (
        <div
          className={styles.velo}
          onClick={() => setAbierto(false)}
          aria-hidden="true"
        />
      )}

      <nav
        id={navId}
        className={`${styles.sidebar} ${abierto ? styles.abierta : ""}`}
        aria-label="Navegación principal"
      >
        <Link href="/" className={styles.marca}>
          <Image
            src="/EsperanzaLogo.png"
            alt="Patio Esperanza"
            width={132}
            height={88}
            priority
          />
        </Link>

        <div className={styles.secciones}>
          {secciones.map((seccion) => (
            <div key={seccion.titulo} className={styles.seccion}>
              <h2 className={styles.tituloSeccion}>{seccion.titulo}</h2>
              <ul className={styles.lista}>
                {seccion.enlaces.map((enlace) => {
                  const activo =
                    pathname === enlace.href || pathname.startsWith(`${enlace.href}/`);
                  return (
                    <li key={enlace.href}>
                      <Link
                        href={enlace.href}
                        className={`${styles.enlace} ${activo ? styles.activo : ""}`}
                        aria-current={activo ? "page" : undefined}
                      >
                        {enlace.texto}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        <div className={styles.sesion}>
          <span className={styles.rol}>{user.rol}</span>
          <button type="button" className={styles.salir} onClick={handleLogout}>
            Salir
          </button>
        </div>
      </nav>
    </>
  );
}
