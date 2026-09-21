import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Field } from "./Field";

describe("Field", () => {
  it("renders a visible label associated with the input", () => {
    render(<Field id="nombre" label="Nombre" placeholder="Escribe tu nombre" />);
    expect(screen.getByText("Nombre")).toBeVisible();
    const input = screen.getByRole("textbox", { name: "Nombre" });
    expect(input).toHaveAttribute("id", "nombre");
    expect(input).not.toHaveAttribute("aria-describedby");
    expect(input).not.toHaveAttribute("aria-invalid");
  });

  it("keeps its hint visible and associated while typing", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Field id="nombre" label="Nombre" hint="Nombre completo" onChange={onChange} />);
    const input = screen.getByRole("textbox", { name: "Nombre" });
    await user.type(input, "Ana");
    expect(input).toHaveValue("Ana");
    expect(onChange).toHaveBeenCalled();
    expect(input).toHaveAttribute("aria-describedby", "nombre-hint");
    expect(input).toHaveAccessibleDescription("Nombre completo");
    expect(screen.getByText("Nombre completo")).toBeVisible();
  });

  it("replaces the hint with an alert and restores it when the error clears", () => {
    const { rerender } = render(<Field id="nombre" label="Nombre" hint="Nombre completo" error="Revisa el nombre" />);
    const input = screen.getByRole("textbox", { name: "Nombre" });
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAttribute("aria-describedby", "nombre-error");
    expect(input).toHaveAccessibleDescription("Revisa el nombre");
    expect(screen.getByRole("alert")).toHaveTextContent("Revisa el nombre");
    expect(screen.queryByText("Nombre completo")).not.toBeInTheDocument();
    rerender(<Field id="nombre" label="Nombre" hint="Nombre completo" />);
    expect(input).not.toHaveAttribute("aria-invalid");
    expect(input).toHaveAccessibleDescription("Nombre completo");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("describes an error without a hint", () => {
    render(<Field id="nombre" label="Nombre" error="Falta el nombre" />);
    expect(screen.getByRole("textbox", { name: "Nombre" })).toHaveAccessibleDescription("Falta el nombre");
    expect(screen.getByRole("alert")).toHaveAttribute("id", "nombre-error");
  });

  it("marks required through the input attribute, keeping the name clean", () => {
    render(<Field id="nombre" label="Nombre" required />);
    // El nombre accesible es solo la etiqueta: el asterisco es decorativo y la obligación
    // la comunica el atributo required, no un texto pegado al nombre del campo.
    expect(screen.getByRole("textbox", { name: "Nombre" })).toBeRequired();
    expect(screen.getByText("*")).toHaveAttribute("aria-hidden", "true");
  });

  it("keeps the label available to assistive tech when hidden visually", () => {
    render(<Field id="horas" label="Anticipación mínima (h)" labelHidden />);
    expect(screen.getByRole("textbox", { name: "Anticipación mínima (h)" })).toBeInTheDocument();
  });

  it("preserves external descriptions and native attributes", () => {
    render(<><p id="externo">Dato privado</p><Field id="nombre" label="Nombre"
      hint="Nombre completo" aria-describedby="externo" disabled name="nombre" defaultValue="Ana" /></>);
    const input = screen.getByRole("textbox", { name: "Nombre" });
    expect(input).toHaveAttribute("aria-describedby", "externo nombre-hint");
    expect(input).toHaveAccessibleDescription("Dato privado Nombre completo");
    expect(input).toBeDisabled();
    expect(input).toHaveValue("Ana");
    expect(input).toHaveAttribute("name", "nombre");
  });

  it("preserves native invalid state but always marks errors invalid", () => {
    const { rerender } = render(<Field id="nombre" label="Nombre" aria-invalid="grammar" />);
    expect(screen.getByRole("textbox")).toHaveAttribute("aria-invalid", "grammar");
    rerender(<Field id="nombre" label="Nombre" aria-invalid={false} error="Revisa el nombre" />);
    expect(screen.getByRole("textbox")).toHaveAttribute("aria-invalid", "true");
  });
});
