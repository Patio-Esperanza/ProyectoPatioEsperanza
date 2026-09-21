import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SugerirUbicacionPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { sugerirUbicacion, listPatios } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, sugerirUbicacion: vi.fn(), listPatios: vi.fn() };
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
  vi.mocked(sugerirUbicacion).mockReset();
  vi.mocked(listPatios).mockReset();
  vi.mocked(listPatios).mockResolvedValue(PATIOS);
});

describe("SugerirUbicacionPage", () => {
  it("shows the suggested slot and its cost", async () => {
    vi.mocked(sugerirUbicacion).mockResolvedValue({
      ubicacion_id: "u1",
      codigo: "A1-T1-S1-N1",
      costo: 1.3,
    });

    const user = userEvent.setup();
    render(<SugerirUbicacionPage />);

    await user.selectOptions(await screen.findByLabelText("Patio"), "p1");
    await user.type(screen.getByLabelText("ID de contenedor"), "c1");
    await user.type(screen.getByLabelText("ID de ubicación de referencia"), "u0");
    await user.click(screen.getByRole("button", { name: "Sugerir" }));

    expect(sugerirUbicacion).toHaveBeenCalledWith("token", {
      patio_id: "p1",
      contenedor_id: "c1",
      punto_referencia_ubicacion_id: "u0",
    });
    expect(await screen.findByText(/A1-T1-S1-N1/)).toBeInTheDocument();
    expect(screen.getByText(/costo 1.30/)).toBeInTheDocument();
  });

  it("shows the backend error when there is no valid slot", async () => {
    const { ApiError } = await import("@/lib/api");
    vi.mocked(sugerirUbicacion).mockRejectedValue(
      new ApiError(409, "No hay ubicaciones disponibles que cumplan las restricciones")
    );

    const user = userEvent.setup();
    render(<SugerirUbicacionPage />);

    await user.selectOptions(await screen.findByLabelText("Patio"), "p1");
    await user.type(screen.getByLabelText("ID de contenedor"), "c1");
    await user.type(screen.getByLabelText("ID de ubicación de referencia"), "u0");
    await user.click(screen.getByRole("button", { name: "Sugerir" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No hay ubicaciones disponibles que cumplan las restricciones"
    );
  });

  it("auto-selects and locks the patio when the user has only one assigned", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "operador", patios: ["p2"] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    render(<SugerirUbicacionPage />);

    const select = await screen.findByLabelText("Patio");
    expect(select).toBeDisabled();
    expect(select).toHaveValue("p2");
  });
});
