import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Card } from "./Card";

describe("Card", () => {
  it("renders its children", () => {
    render(<Card><h2>Contenedor</h2><p>Disponible</p></Card>);
    expect(screen.getByRole("heading", { name: "Contenedor" })).toBeInTheDocument();
    expect(screen.getByText("Disponible")).toBeInTheDocument();
  });

  it("accepts an additional class without changing content semantics", () => {
    render(<Card className="detalle"><a href="/contenedores">Ver contenedores</a></Card>);
    expect(screen.getByRole("link", { name: "Ver contenedores" })).toHaveAttribute("href", "/contenedores");
  });
});
