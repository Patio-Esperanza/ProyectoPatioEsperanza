import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MisContenedoresPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { listarContenedores, listPatios, solicitarSalida } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    listarContenedores: vi.fn(),
    listPatios: vi.fn(),
    solicitarSalida: vi.fn(),
  };
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
  vi.mocked(listPatios).mockReset();
  vi.mocked(solicitarSalida).mockReset();
});

describe("MisContenedoresPage", () => {
  it("shows a not-authorized message for non-cliente roles", async () => {
    mockAuth("operador");

    render(<MisContenedoresPage />);

    expect(
      screen.getByRole("heading", { name: "No tienes permiso para ver esta página" })
    ).toBeInTheDocument();
  });

  it("lists the client's contenedores and shows Solicitar salida only for ubicado", async () => {
    mockAuth("cliente");
    vi.mocked(listarContenedores).mockResolvedValue([
      {
        id: "c1",
        numero_contenedor: "CSQU3054383",
        tipo: "lleno",
        tamano: "40",
        patio_id: "p1",
        estado: "ubicado",
        peso_kg: 18000,
      },
      {
        id: "c2",
        numero_contenedor: "TRHU1866154",
        tipo: "lleno",
        tamano: "20",
        patio_id: "p1",
        estado: "solicitud_ingreso",
        peso_kg: 12000,
      },
    ]);
    vi.mocked(listPatios).mockResolvedValue([
      { id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 },
    ]);

    render(<MisContenedoresPage />);

    expect(await screen.findByText(/CSQU3054383/)).toBeInTheDocument();
    expect(screen.getByText(/TRHU1866154/)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Solicitar salida" })).toHaveLength(1);
    await userEvent.setup().click(screen.getByRole("button", { name: "Solicitar salida" }));
    expect(screen.getByText(/24 horas/)).toBeInTheDocument();
  });

  it("submits a solicitud de salida", async () => {
    mockAuth("cliente");
    vi.mocked(listarContenedores).mockResolvedValueOnce([
      {
        id: "c1",
        numero_contenedor: "CSQU3054383",
        tipo: "lleno",
        tamano: "40",
        patio_id: "p1",
        estado: "ubicado",
        peso_kg: 18000,
      },
    ]);
    vi.mocked(listarContenedores).mockResolvedValue([
      {
        id: "c1",
        numero_contenedor: "CSQU3054383",
        tipo: "lleno",
        tamano: "40",
        patio_id: "p1",
        estado: "solicitud_salida",
        peso_kg: 18000,
      },
    ]);
    vi.mocked(listPatios).mockResolvedValue([
      { id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 },
    ]);
    vi.mocked(solicitarSalida).mockResolvedValue({
      id: "c1",
      numero_contenedor: "CSQU3054383",
      tipo: "lleno",
      tamano: "40",
      patio_id: "p1",
      estado: "solicitud_salida",
      peso_kg: 18000,
    });

    const user = userEvent.setup();
    render(<MisContenedoresPage />);

    await user.click(await screen.findByRole("button", { name: "Solicitar salida" }));
    await user.type(screen.getByLabelText("Fecha y hora deseada"), "2026-10-05T12:00");
    await user.click(screen.getByRole("button", { name: "Confirmar solicitud" }));

    expect(solicitarSalida).toHaveBeenCalledWith("token", "c1", "2026-10-05T12:00");
    expect(await screen.findByText(/solicitud_salida/)).toBeInTheDocument();
  });
});
