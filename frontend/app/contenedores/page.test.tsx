import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ContenedoresPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { createContenedor, listPatios } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, createContenedor: vi.fn(), listPatios: vi.fn() };
});

const PATIOS = [
  { id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 },
  { id: "p2", nombre: "Patio Sur", codigo: "PS", activo: true, anticipacion_minima_horas: 24 },
];

beforeEach(() => {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "1", rol: "operador", patios: ["p1", "p2"] },
    token: "token",
    ready: true,
    setToken: vi.fn(),
    logout: vi.fn(),
  });
  vi.mocked(createContenedor).mockReset();
  vi.mocked(listPatios).mockReset();
  vi.mocked(listPatios).mockResolvedValue(PATIOS);
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
    await user.selectOptions(await screen.findByLabelText("Patio"), "p1");
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
    await user.selectOptions(await screen.findByLabelText("Patio"), "p1");
    await user.type(screen.getByLabelText("Peso (kg)"), "18000");
    await user.click(screen.getByRole("button", { name: "Crear contenedor" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "numero_contenedor no cumple el checksum ISO 6346"
    );
  });

  it("auto-selects and locks the patio when the user has only one assigned", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "operador", patios: ["p1"] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    render(<ContenedoresPage />);

    const select = await screen.findByLabelText("Patio");
    expect(select).toBeDisabled();
    expect(select).toHaveValue("p1");
  });
});
