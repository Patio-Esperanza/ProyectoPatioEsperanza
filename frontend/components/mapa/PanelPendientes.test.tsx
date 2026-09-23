import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PanelPendientes } from "./PanelPendientes";
import type { Contenedor } from "@/lib/api";

const CONTENEDORES: Contenedor[] = [
  {
    id: "c1",
    numero_contenedor: "MSCU1234567",
    tipo: "lleno",
    tamano: "40",
    patio_id: "p1",
    estado: "ingresado",
    peso_kg: 18000,
  },
  {
    id: "c2",
    numero_contenedor: "TCLU7654321",
    tipo: "vacio",
    tamano: "20",
    patio_id: "p1",
    estado: "ingresado",
    peso_kg: 3900,
  },
];

describe("PanelPendientes", () => {
  it("lista los contenedores por ubicar", () => {
    render(
      <PanelPendientes
        contenedores={CONTENEDORES}
        seleccionadoId={null}
        cargando={false}
        onSeleccionar={vi.fn()}
      />
    );
    expect(screen.getByText("MSCU1234567")).toBeVisible();
    expect(screen.getByText("TCLU7654321")).toBeVisible();
  });

  it("avisa cuando no hay pendientes", () => {
    render(
      <PanelPendientes
        contenedores={[]}
        seleccionadoId={null}
        cargando={false}
        onSeleccionar={vi.fn()}
      />
    );
    expect(screen.getByText("No hay contenedores por ubicar")).toBeVisible();
  });

  it("marca el contenedor elegido con aria-pressed", () => {
    render(
      <PanelPendientes
        contenedores={CONTENEDORES}
        seleccionadoId="c2"
        cargando={false}
        onSeleccionar={vi.fn()}
      />
    );
    expect(screen.getByRole("button", { name: /TCLU7654321/ })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
  });

  it("avisa el id del contenedor al elegirlo", async () => {
    const onSeleccionar = vi.fn();
    render(
      <PanelPendientes
        contenedores={CONTENEDORES}
        seleccionadoId={null}
        cargando={false}
        onSeleccionar={onSeleccionar}
      />
    );
    await userEvent.click(screen.getByRole("button", { name: /MSCU1234567/ }));
    expect(onSeleccionar).toHaveBeenCalledWith("c1");
  });
});
