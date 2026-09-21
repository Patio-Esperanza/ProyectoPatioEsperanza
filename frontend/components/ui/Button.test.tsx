import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "./Button";

describe("Button", () => {
  it("renders an enabled button by default", () => {
    render(<Button>Guardar</Button>);
    const button = screen.getByRole("button", { name: "Guardar" });
    expect(button).toBeEnabled();
    expect(button).toHaveAttribute("type", "button");
    expect(button).not.toHaveAttribute("aria-busy");
  });

  it.each(["primary", "secondary", "danger", "ghost"] as const)(
    "supports the %s variant and click events", async (variant) => {
      const onClick = vi.fn();
      const user = userEvent.setup();
      render(<Button variant={variant} onClick={onClick}>Guardar</Button>);
      await user.click(screen.getByRole("button", { name: "Guardar" }));
      expect(onClick).toHaveBeenCalledOnce();
    }
  );

  it.each(["sm", "md"] as const)("supports size %s", (size) => {
    render(<Button size={size}>Guardar</Button>);
    expect(screen.getByRole("button", { name: "Guardar" })).toBeEnabled();
  });

  it("keeps its label and blocks clicks while loading", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<Button loading disabled={false} onClick={onClick}>Guardar</Button>);
    const button = screen.getByRole("button", { name: "Guardar" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    const spinner = button.querySelector("svg");
    expect(spinner).toHaveAttribute("aria-hidden", "true");
    expect(spinner).toHaveAttribute("width", "20");
    expect(spinner).toHaveAttribute("height", "20");
    expect(spinner).toHaveAttribute("stroke-width", "1.5");
    await user.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("preserves native attributes and disabled after loading ends", () => {
    const { rerender } = render(<Button loading disabled type="submit" name="guardar">Guardar</Button>);
    rerender(<Button disabled type="submit" name="guardar">Guardar</Button>);
    const button = screen.getByRole("button", { name: "Guardar" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("type", "submit");
    expect(button).toHaveAttribute("name", "guardar");
    expect(button).not.toHaveAttribute("aria-busy");
    expect(button.querySelector("svg")).not.toBeInTheDocument();
  });

  it("becomes enabled when loading ends", () => {
    const { rerender } = render(<Button loading>Guardar</Button>);
    rerender(<Button>Guardar</Button>);
    expect(screen.getByRole("button", { name: "Guardar" })).toBeEnabled();
  });
});
