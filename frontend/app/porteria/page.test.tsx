import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PorteriaPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { verificarPin } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, verificarPin: vi.fn() };
});

function mockAuth(rol: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "1", rol, patios: [] },
    token: "token",
    ready: true,
    setToken: vi.fn(),
    logout: vi.fn(),
  });
}

beforeEach(() => {
  vi.mocked(verificarPin).mockReset();
});

describe("PorteriaPage", () => {
  it("shows a not-authorized message for cliente role", () => {
    mockAuth("cliente");

    render(<PorteriaPage />);

    expect(
      screen.getByRole("heading", { name: "No tienes permiso para ver esta página" })
    ).toBeInTheDocument();
  });

  it("submits numero_contenedor and pin, shows success", async () => {
    mockAuth("operador");
    vi.mocked(verificarPin).mockResolvedValue({
      id: "c1",
      numero_contenedor: "CSQU3054383",
      tipo: "lleno",
      tamano: "40",
      patio_id: "p1",
      estado: "en_porteria",
      peso_kg: 18000,
    });

    const user = userEvent.setup();
    render(<PorteriaPage />);

    await user.type(screen.getByLabelText("Número de contenedor"), "CSQU3054383");
    await user.type(screen.getByLabelText("PIN"), "4821");
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    expect(verificarPin).toHaveBeenCalledWith("token", {
      numero_contenedor: "CSQU3054383",
      pin: "4821",
    });
    expect(await screen.findByText(/en_porteria/)).toBeInTheDocument();
  });

  it("shows the API error message on failure", async () => {
    mockAuth("operador");
    const { ApiError } = await import("@/lib/api");
    vi.mocked(verificarPin).mockRejectedValue(new ApiError(422, "PIN incorrecto"));

    const user = userEvent.setup();
    render(<PorteriaPage />);

    await user.type(screen.getByLabelText("Número de contenedor"), "CSQU3054383");
    await user.type(screen.getByLabelText("PIN"), "0000");
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("PIN incorrecto");
  });
});
