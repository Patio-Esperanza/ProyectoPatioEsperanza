import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { Alert } from "./Alert";

describe("Alert", () => {
  it.each([
    ["info", "status"], ["success", "status"], ["warning", "alert"], ["danger", "alert"],
  ] as const)("announces tone %s with role %s", (tone, role) => {
    render(<Alert tone={tone}>Revisa el estado del contenedor.</Alert>);
    const alert = screen.getByRole(role);
    expect(alert).toHaveTextContent("Revisa el estado del contenedor.");
    const icon = alert.querySelector("svg");
    expect(icon).toHaveAttribute("aria-hidden", "true");
    expect(icon).toHaveAttribute("width", "20");
    expect(icon).toHaveAttribute("height", "20");
    expect(icon).toHaveAttribute("stroke", "currentColor");
    expect(icon).toHaveAttribute("stroke-width", "1.5");
    expect(within(alert).queryByRole("img")).not.toBeInTheDocument();
  });

  it("renders an optional title and rich content", () => {
    render(<Alert tone="success" titulo="Registro guardado"><a href="/contenedores">Ver contenedores</a></Alert>);
    const status = screen.getByRole("status");
    expect(within(status).getByText("Registro guardado")).toBeVisible();
    expect(within(status).getByRole("link", { name: "Ver contenedores" })).toHaveAttribute("href", "/contenedores");
  });
});
