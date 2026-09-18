import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ContenedoresPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { createContenedor } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, createContenedor: vi.fn() };
});

beforeEach(() => {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "1", rol: "operador", patios: [] },
    token: "token",
    ready: true,
    setToken: vi.fn(),
    logout: vi.fn(),
  });
  vi.mocked(createContenedor).mockReset();
});

describe("ContenedoresPage", () => {
  it("creates a contenedor with the form values", async () => {
    vi.mocked(createContenedor).mockResolvedValue({
      id: "c1",
      numero_contenedor: "CSQU3054383",
      tipo: "lleno",
      tamano: "40",
      patio_id: "p1",
      estado: "solicitud_ingreso",
      peso_kg: 18000,
    });

    const user = userEvent.setup();
    render(<ContenedoresPage />);

    await user.type(screen.getByLabelText("Número de contenedor"), "CSQU3054383");
    await user.type(screen.getByLabelText("ID de patio"), "p1");
    await user.type(screen.getByLabelText("Peso (kg)"), "18000");
    await user.click(screen.getByRole("button", { name: "Crear contenedor" }));

    expect(createContenedor).toHaveBeenCalledWith("token", {
      numero_contenedor: "CSQU3054383",
      tipo: "lleno",
      tamano: "40",
      patio_id: "p1",
      peso_kg: 18000,
    });
    expect(await screen.findByText(/estado solicitud_ingreso/)).toBeInTheDocument();
  });

  it("shows the backend error message on failure", async () => {
    const { ApiError } = await import("@/lib/api");
    vi.mocked(createContenedor).mockRejectedValue(
      new ApiError(422, "numero_contenedor no cumple el checksum ISO 6346")
    );

    const user = userEvent.setup();
    render(<ContenedoresPage />);

    await user.type(screen.getByLabelText("Número de contenedor"), "CSQU3054380");
    await user.type(screen.getByLabelText("ID de patio"), "p1");
    await user.type(screen.getByLabelText("Peso (kg)"), "18000");
    await user.click(screen.getByRole("button", { name: "Crear contenedor" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "numero_contenedor no cumple el checksum ISO 6346"
    );
  });
});
