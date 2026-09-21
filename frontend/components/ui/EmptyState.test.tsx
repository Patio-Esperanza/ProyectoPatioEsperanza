import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EmptyState } from "./EmptyState";
import { Button } from "./Button";

describe("EmptyState", () => {
  it("renders its title without optional content", () => {
    render(<EmptyState titulo="Sin contenedores" />);
    expect(screen.getByRole("heading", { level: 2, name: "Sin contenedores" })).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("renders a description and a working action", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<EmptyState titulo="Sin contenedores" descripcion="Registra tu primer contenedor."
      accion={<Button onClick={onClick}>Registrar</Button>} />);
    expect(screen.getByText("Registra tu primer contenedor.")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Registrar" }));
    expect(onClick).toHaveBeenCalledOnce();
  });
});
