"use client";

import { useEffect } from "react";
import { usePatiosDisponibles } from "@/lib/use-patios-disponibles";

interface PatioSelectProps {
  id: string;
  value: string;
  onChange: (patioId: string) => void;
}

export function PatioSelect({ id, value, onChange }: PatioSelectProps) {
  const { patios, loading } = usePatiosDisponibles();

  useEffect(() => {
    if (patios.length === 1 && value !== patios[0].id) {
      onChange(patios[0].id);
    }
  }, [patios, value, onChange]);

  if (loading) return <p>Cargando patios...</p>;
  if (patios.length === 0) return <p>No tienes patios asignados.</p>;

  return (
    <select
      id={id}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={patios.length === 1}
      required
    >
      {patios.length > 1 && <option value="">Selecciona un patio</option>}
      {patios.map((patio) => (
        <option key={patio.id} value={patio.id}>
          {patio.nombre} ({patio.codigo})
        </option>
      ))}
    </select>
  );
}
