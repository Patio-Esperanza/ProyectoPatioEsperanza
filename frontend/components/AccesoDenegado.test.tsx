import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AccesoDenegado } from "./AccesoDenegado";

describe("AccesoDenegado", () => {
  it("explains the block and names the current role", () => {
    render(<AccesoDenegado rol="cliente" />);

    expect(screen.getByRole("heading", { name: "No tienes permiso para ver esta página" }))
      .toBeInTheDocument();
    expect(screen.getByText("cliente")).toBeInTheDocument();
  });

  it("links a cliente back to Mis contenedores", () => {
    render(<AccesoDenegado rol="cliente" />);

    expect(screen.getByRole("link", { name: "Ir al inicio" })).toHaveAttribute(
      "href",
      "/mis-contenedores"
    );
  });

  it("links a staff role back to Patios", () => {
    render(<AccesoDenegado rol="operador" />);

    expect(screen.getByRole("link", { name: "Ir al inicio" })).toHaveAttribute(
      "href",
      "/patios"
    );
  });
});
