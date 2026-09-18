import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ContenedorDetallePage from "./page";
import { useAuth } from "@/lib/auth-context";
import { getContenedor, ApiError } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  useParams: () => ({ id: "c1" }),
}));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, getContenedor: vi.fn() };
});

beforeEach(() => {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "1", rol: "operador", patios: [] },
    token: "token",
    ready: true,
    setToken: vi.fn(),
    logout: vi.fn(),
  });
  vi.mocked(getContenedor).mockReset();
});

describe("ContenedorDetallePage", () => {
  it("shows the container fetched by id", async () => {
    vi.mocked(getContenedor).mockResolvedValue({
      id: "c1",
      numero_contenedor: "CSQU3054383",
      tipo: "lleno",
      tamano: "40",
      patio_id: "p1",
      estado: "ubicado",
      peso_kg: 18000,
    });

    render(<ContenedorDetallePage />);

    expect(await screen.findByText("CSQU3054383")).toBeInTheDocument();
    expect(screen.getByText("ubicado")).toBeInTheDocument();
    expect(getContenedor).toHaveBeenCalledWith("token", "c1");
  });

  it("shows an error when the container is not found or hidden by RLS", async () => {
    vi.mocked(getContenedor).mockRejectedValue(new ApiError(404, "Contenedor no encontrado"));

    render(<ContenedorDetallePage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Contenedor no encontrado");
  });
});
