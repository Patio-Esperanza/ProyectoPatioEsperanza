import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DetalleTira } from "./DetalleTira";
import type { DetalleTira as DetalleTiraData } from "@/lib/api";

const DETALLE: DetalleTiraData = {
  tira_id: "t1",
  codigo: "A1-T1-R1",
  niveles: [
    {
      nivel: 1,
      ubicacion_id: "u1",
      codigo: "A1-T1-R1-N1",
      activo: true,
      capacidad_peso_kg: 30000,
      contenedor: {
        id: "c1",
        numero_contenedor: "CAIU1112223",
        tipo: "lleno",
        tamano: "40",
        peso_kg: 28000,
        estado: "ubicado",
      },
    },
    {
      nivel: 2,
      ubicacion_id: "u2",
      codigo: "A1-T1-R1-N2",
      activo: true,
      capacidad_peso_kg: 30000,
      contenedor: null,
    },
  ],
};

describe("DetalleTira", () => {
  it("muestra el contenedor del nivel ocupado", () => {
    render(
      <DetalleTira
        detalle={DETALLE}
        contenedorSeleccionado={null}
        ubicacionSugeridaId={null}
        colocando={false}
        onColocar={vi.fn()}
      />
    );
    expect(screen.getByText("CAIU1112223")).toBeVisible();
  });

  it("marca el nivel libre como libre", () => {
    render(
      <DetalleTira
        detalle={DETALLE}
        contenedorSeleccionado={null}
        ubicacionSugeridaId={null}
        colocando={false}
        onColocar={vi.fn()}
      />
    );
    expect(screen.getByText("Libre")).toBeVisible();
  });

  it("no ofrece colocar si no hay contenedor seleccionado", () => {
    render(
      <DetalleTira
        detalle={DETALLE}
        contenedorSeleccionado={null}
        ubicacionSugeridaId={null}
        colocando={false}
        onColocar={vi.fn()}
      />
    );
    expect(screen.queryByRole("button", { name: /Colocar aquí/ })).not.toBeInTheDocument();
  });

  it("coloca sin motivo cuando el nivel es el sugerido", async () => {
    const onColocar = vi.fn();
    render(
      <DetalleTira
        detalle={DETALLE}
        contenedorSeleccionado="c9"
        ubicacionSugeridaId="u2"
        colocando={false}
        onColocar={onColocar}
      />
    );
    await userEvent.click(screen.getByRole("button", { name: "Colocar aquí" }));
    expect(onColocar).toHaveBeenCalledWith("u2", null);
  });

  it("exige motivo cuando el nivel no es el sugerido", async () => {
    const onColocar = vi.fn();
    render(
      <DetalleTira
        detalle={DETALLE}
        contenedorSeleccionado="c9"
        ubicacionSugeridaId="u7"
        colocando={false}
        onColocar={onColocar}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: "Colocar aquí" }));
    expect(onColocar).not.toHaveBeenCalled();

    await userEvent.type(
      screen.getByLabelText("Motivo para no usar la ubicación sugerida"),
      "Equipo en mantenimiento"
    );
    await userEvent.click(screen.getByRole("button", { name: "Confirmar colocación" }));
    expect(onColocar).toHaveBeenCalledWith("u2", "Equipo en mantenimiento");
  });
});
