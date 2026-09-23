import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CeldaTira } from "./CeldaTira";
import type { TiraMapa } from "@/lib/api";

function tira(overrides: Partial<TiraMapa> = {}): TiraMapa {
  return {
    id: "t1",
    codigo: "R1",
    orden: 0,
    niveles_totales: 5,
    niveles_activos: 5,
    niveles_ocupados: 3,
    ...overrides,
  };
}

describe("CeldaTira", () => {
  it("imprime la ocupacion como texto, no solo con color", () => {
    render(
      <CeldaTira
        tira={tira()}
        carrilCodigo="A1"
        tramoCodigo="T1"
        seleccionada={false}
        sugerida={false}
        tabIndex={0}
        onSeleccionar={vi.fn()}
      />
    );
    expect(screen.getByText("3/5")).toBeVisible();
  });

  it("describe la celda completa para lectores de pantalla", () => {
    render(
      <CeldaTira
        tira={tira()}
        carrilCodigo="A1"
        tramoCodigo="T1"
        seleccionada={false}
        sugerida={false}
        tabIndex={0}
        onSeleccionar={vi.fn()}
      />
    );
    expect(
      screen.getByRole("gridcell", {
        name: "Carril A1, tramo T1, tira R1, 3 de 5 niveles ocupados",
      })
    ).toBeVisible();
  });

  it("anuncia que esta sugerida", () => {
    render(
      <CeldaTira
        tira={tira()}
        carrilCodigo="A1"
        tramoCodigo="T1"
        seleccionada={false}
        sugerida
        tabIndex={0}
        onSeleccionar={vi.fn()}
      />
    );
    expect(screen.getByText("Sugerido")).toBeVisible();
  });

  it("marca la seleccion con aria-selected", () => {
    render(
      <CeldaTira
        tira={tira()}
        carrilCodigo="A1"
        tramoCodigo="T1"
        seleccionada
        sugerida={false}
        tabIndex={0}
        onSeleccionar={vi.fn()}
      />
    );
    expect(screen.getByRole("gridcell")).toHaveAttribute("aria-selected", "true");
  });

  it("avisa cuando la tira esta inactiva y no deja seleccionarla", async () => {
    const onSeleccionar = vi.fn();
    render(
      <CeldaTira
        tira={tira({ niveles_activos: 0, niveles_ocupados: 0 })}
        carrilCodigo="A1"
        tramoCodigo="T1"
        seleccionada={false}
        sugerida={false}
        tabIndex={0}
        onSeleccionar={onSeleccionar}
      />
    );
    const celda = screen.getByRole("gridcell");
    expect(celda).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(celda);
    expect(onSeleccionar).not.toHaveBeenCalled();
  });

  it("llama onSeleccionar con el id de la tira", async () => {
    const onSeleccionar = vi.fn();
    render(
      <CeldaTira
        tira={tira()}
        carrilCodigo="A1"
        tramoCodigo="T1"
        seleccionada={false}
        sugerida={false}
        tabIndex={0}
        onSeleccionar={onSeleccionar}
      />
    );
    await userEvent.click(screen.getByRole("gridcell"));
    expect(onSeleccionar).toHaveBeenCalledWith("t1");
  });
});
