import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MovimientosPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { crearMovimiento } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, crearMovimiento: vi.fn() };
});

beforeEach(() => {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "1", rol: "operador", patios: [] },
    token: "token",
    ready: true,
    setToken: vi.fn(),
    logout: vi.fn(),
  });
  vi.mocked(crearMovimiento).mockReset();
});

describe("MovimientosPage", () => {
  it("registers a movimiento with the form values", async () => {
    vi.mocked(crearMovimiento).mockResolvedValue({
      id: "m1",
      contenedor_id: "c1",
      ubicacion_destino_id: "u1",
      tipo: "ingreso",
    });

    const user = userEvent.setup();
    render(<MovimientosPage />);

    await user.type(screen.getByLabelText("ID de contenedor"), "c1");
    await user.type(screen.getByLabelText("ID de ubicación destino"), "u1");
    await user.click(screen.getByRole("button", { name: "Registrar movimiento" }));

    expect(crearMovimiento).toHaveBeenCalledWith("token", {
      contenedor_id: "c1",
      ubicacion_destino_id: "u1",
      tipo: "ingreso",
    });
    expect(await screen.findByText(/Movimiento m1 registrado/)).toBeInTheDocument();
  });

  it("shows the backend error when the slot is already occupied", async () => {
    const { ApiError } = await import("@/lib/api");
    vi.mocked(crearMovimiento).mockRejectedValue(new ApiError(409, "Ubicación ya ocupada"));

    const user = userEvent.setup();
    render(<MovimientosPage />);

    await user.type(screen.getByLabelText("ID de contenedor"), "c1");
    await user.type(screen.getByLabelText("ID de ubicación destino"), "u1");
    await user.click(screen.getByRole("button", { name: "Registrar movimiento" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Ubicación ya ocupada");
  });
});
