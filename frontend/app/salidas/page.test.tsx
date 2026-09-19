import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import SalidasPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { listarContenedores } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, listarContenedores: vi.fn(), listPatios: vi.fn() };
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
  vi.mocked(listarContenedores).mockReset();
});

describe("SalidasPage", () => {
  it("shows a not-authorized message for cliente role", () => {
    mockAuth("cliente");
    vi.mocked(listarContenedores).mockResolvedValue([]);

    render(<SalidasPage />);

    expect(screen.getByRole("alert")).toHaveTextContent("No autorizado");
  });

  it("lists pending salida requests ordered by fecha_deseada_salida", async () => {
    mockAuth("operador");
    vi.mocked(listarContenedores).mockResolvedValue([
      {
        id: "c1",
        numero_contenedor: "CSQU3054383",
        tipo: "lleno",
        tamano: "40",
        patio_id: "p1",
        estado: "solicitud_salida",
        peso_kg: 18000,
        fecha_deseada_salida: "2026-10-05T12:00:00Z",
      },
    ]);

    render(<SalidasPage />);

    await waitFor(() =>
      expect(listarContenedores).toHaveBeenCalledWith("token", { estado: "solicitud_salida" })
    );
    expect(await screen.findByText(/CSQU3054383/)).toBeInTheDocument();
  });
});
