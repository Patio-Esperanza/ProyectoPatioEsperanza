import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MapaPatio } from "./MapaPatio";
import type { MapaPatio as MapaPatioData } from "@/lib/api";

const MAPA: MapaPatioData = {
  patio_id: "p1",
  ubicacion_entrada_id: "u1",
  resumen: { ubicaciones_activas: 20, ocupadas: 7 },
  carriles: [
    {
      id: "c1",
      codigo: "A1",
      orden: 0,
      tipo_teorico: "lleno",
      tramos: [
        {
          id: "tr1",
          codigo: "T1",
          orden: 0,
          tiras: [
            { id: "t1", codigo: "R1", orden: 0, niveles_totales: 5, niveles_activos: 5, niveles_ocupados: 5 },
            { id: "t2", codigo: "R2", orden: 1, niveles_totales: 5, niveles_activos: 5, niveles_ocupados: 2 },
          ],
        },
      ],
    },
    {
      id: "c2",
      codigo: "A2",
      orden: 1,
      tipo_teorico: null,
      tramos: [
        {
          id: "tr2",
          codigo: "T1",
          orden: 0,
          tiras: [
            { id: "t3", codigo: "R1", orden: 0, niveles_totales: 5, niveles_activos: 5, niveles_ocupados: 0 },
          ],
        },
      ],
    },
  ],
};

describe("MapaPatio", () => {
  it("agrupa las tiras por carril y por tramo", () => {
    render(
      <MapaPatio
        mapa={MAPA}
        tiraSeleccionadaId={null}
        tiraSugeridaId={null}
        onSeleccionarTira={vi.fn()}
      />
    );
    const carrilA1 = screen.getByRole("group", { name: /Carril A1/ });
    expect(within(carrilA1).getAllByRole("gridcell")).toHaveLength(2);
  });

  it("muestra el resumen de ocupacion del patio", () => {
    render(
      <MapaPatio
        mapa={MAPA}
        tiraSeleccionadaId={null}
        tiraSugeridaId={null}
        onSeleccionarTira={vi.fn()}
      />
    );
    expect(screen.getByText("7 de 20 ubicaciones ocupadas")).toBeVisible();
  });

  it("filtra a un solo carril", async () => {
    render(
      <MapaPatio
        mapa={MAPA}
        tiraSeleccionadaId={null}
        tiraSugeridaId={null}
        onSeleccionarTira={vi.fn()}
      />
    );
    await userEvent.selectOptions(screen.getByLabelText("Filtrar por carril"), "c2");
    expect(screen.queryByRole("group", { name: /Carril A1/ })).not.toBeInTheDocument();
    expect(screen.getByRole("group", { name: /Carril A2/ })).toBeVisible();
  });

  it("expone un solo tab stop y mueve el foco con las flechas", async () => {
    render(
      <MapaPatio
        mapa={MAPA}
        tiraSeleccionadaId={null}
        tiraSugeridaId={null}
        onSeleccionarTira={vi.fn()}
      />
    );
    const celdas = screen.getAllByRole("gridcell");
    expect(celdas.filter((c) => c.getAttribute("tabindex") === "0")).toHaveLength(1);

    await userEvent.tab();
    expect(celdas[0]).toHaveFocus();
    await userEvent.keyboard("{ArrowRight}");
    expect(celdas[1]).toHaveFocus();
    await userEvent.keyboard("{ArrowLeft}");
    expect(celdas[0]).toHaveFocus();
  });

  it("marca la tira sugerida", () => {
    render(
      <MapaPatio
        mapa={MAPA}
        tiraSeleccionadaId={null}
        tiraSugeridaId="t2"
        onSeleccionarTira={vi.fn()}
      />
    );
    expect(screen.getByText("Sugerido")).toBeVisible();
  });
});
