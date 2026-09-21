"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
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
