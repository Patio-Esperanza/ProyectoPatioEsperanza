"use client";

import { useEffect, useState } from "react";
import { useAuth } from "./auth-context";
import { listPatios, type Patio } from "./api";

export interface PatiosDisponibles {
  patios: Patio[];
  loading: boolean;
}

export function usePatiosDisponibles(): PatiosDisponibles {
  const { token, user } = useAuth();
  const [patios, setPatios] = useState<Patio[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token || !user) return;
    let cancelado = false;
    listPatios(token)
      .then((todos) => {
        if (cancelado) return;
        const disponibles =
          user.rol === "admin" ? todos : todos.filter((patio) => user.patios.includes(patio.id));
        setPatios(disponibles);
      })
      .finally(() => {
        if (!cancelado) setLoading(false);
      });
    return () => {
      cancelado = true;
    };
  }, [token, user]);

  return { patios, loading };
}
