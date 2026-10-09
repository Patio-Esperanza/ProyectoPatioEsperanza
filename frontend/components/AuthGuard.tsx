"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { guardarRutaRetorno } from "@/lib/ruta-retorno";
import { AccesoDenegado } from "./AccesoDenegado";

interface AuthGuardProps {
  children: ReactNode;
  /**
   * Roles que pueden ver el contenido. Sin esta prop el guard solo exige que haya sesión.
   * Con ella, un rol fuera de la lista recibe la pantalla de acceso denegado en vez de un
   * redirect: el redirect silencioso deja al usuario sin saber qué pasó.
   */
  roles?: string[];
}

export function AuthGuard({ children, roles }: AuthGuardProps) {
  const { user, ready } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (ready && !user) {
      // Se guarda antes del redirect: después de iniciar sesión el usuario regresa a la
      // página donde estaba trabajando, no a la pantalla inicial. La ruta se lee de
      // `window.location` y no de `useSearchParams` porque ese hook obliga a envolver cada
      // página en un Suspense para compilar, y aquí el efecto ya corre solo en el navegador.
      guardarRutaRetorno(window.location.pathname + window.location.search);
      router.replace("/login");
    }
  }, [ready, user, router]);

  if (!ready || !user) {
    return null;
  }

  if (roles && !roles.includes(user.rol)) {
    return <AccesoDenegado rol={user.rol} />;
  }

  return <>{children}</>;
}
