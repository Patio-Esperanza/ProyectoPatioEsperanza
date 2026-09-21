import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SolicitarPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { solicitarContenedor } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, solicitarContenedor: vi.fn() };
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
  vi.mocked(solicitarContenedor).mockReset();
});

describe("SolicitarPage", () => {
  it("shows a not-authorized message for non-cliente roles", () => {
    mockAuth("operador");

    render(<SolicitarPage />);

    expect(
      screen.getByRole("heading", { name: "No tienes permiso para ver esta página" })
    ).toBeInTheDocument();
  });

  it("submits a solicitud with the form values", async () => {
    mockAuth("cliente");
    vi.mocked(solicitarContenedor).mockResolvedValue({
      id: "c1",
      numero_contenedor: "CSQU3054383",
      tipo: "lleno",
      tamano: "40",
      patio_id: "p1",
      estado: "solicitud_ingreso",
      peso_kg: 18000,
      fecha_estimada_retiro: "2026-10-01T00:00:00+00:00",
    });

    const user = userEvent.setup();
    render(<SolicitarPage />);

    await user.type(screen.getByLabelText("Número de contenedor"), "CSQU3054383");
    await user.type(screen.getByLabelText("Peso (kg)"), "18000");
    await user.click(screen.getByRole("button", { name: "Enviar solicitud" }));

    expect(solicitarContenedor).toHaveBeenCalledWith("token", {
      numero_contenedor: "CSQU3054383",
      tipo: "lleno",
      tamano: "40",
      peso_kg: 18000,
      fecha_estimada_retiro: undefined,
    });
    expect(await screen.findByText(/estado solicitud_ingreso/)).toBeInTheDocument();
  });
});
