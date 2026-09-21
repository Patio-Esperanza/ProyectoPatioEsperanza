import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PageHeader } from "./PageHeader";
import { Button } from "./Button";

describe("PageHeader", () => {
  it("renders the page title as h1", () => {
    render(<PageHeader titulo="Contenedores" />);
    expect(screen.getByRole("heading", { level: 1, name: "Contenedores" })).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("renders the description and action after the title", () => {
    render(<PageHeader titulo="Contenedores" descripcion="Consulta el inventario del patio."
      accion={<Button>Registrar</Button>} />);
    const title = screen.getByRole("heading", { level: 1, name: "Contenedores" });
    const action = screen.getByRole("button", { name: "Registrar" });
    expect(screen.getByText("Consulta el inventario del patio.")).toBeVisible();
    expect(action).toBeEnabled();
    expect(title.compareDocumentPosition(action) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});
