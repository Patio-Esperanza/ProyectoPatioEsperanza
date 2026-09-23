import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MapaPage from "./page";
import { useAuth } from "@/lib/auth-context";
import {
  ApiError,
  crearMovimiento,
  listPatios,
  listarContenedores,
  obtenerDetalleTira,
  obtenerMapaPatio,
  sugerirUbicacion,
} from "@/lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    listPatios: vi.fn(),
    listarContenedores: vi.fn(),
    obtenerMapaPatio: vi.fn(),
    obtenerDetalleTira: vi.fn(),
    sugerirUbicacion: vi.fn(),
    crearMovimiento: vi.fn(),
  };
});

const PATIOS = [
  { id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 },
];

const MAPA = {
  patio_id: "p1",
  ubicacion_entrada_id: "u0",
  resumen: { ubicaciones_activas: 5, ocupadas: 0 },
  carriles: [
    {
      id: "c1",
      codigo: "A1",
      orden: 0,
      tipo_teorico: null,
      tramos: [
        {
          id: "tr1",
          codigo: "T1",
          orden: 0,
          tiras: [
            { id: "t1", codigo: "R1", orden: 0, niveles_totales: 5, niveles_activos: 5, niveles_ocupados: 0 },
          ],
        },
      ],
    },
  ],
};

const DETALLE = {
  tira_id: "t1",
  codigo: "A1-T1-R1",
  niveles: [
    {
      nivel: 1,
      ubicacion_id: "u1",
      codigo: "A1-T1-R1-N1",
      activo: true,
      capacidad_peso_kg: 30000,
      contenedor: null,
    },
  ],
};

const PENDIENTES = [
  {
    id: "c9",
    numero_contenedor: "MSCU1234567",
    tipo: "lleno" as const,
    tamano: "40" as const,
    patio_id: "p1",
    estado: "ingresado" as const,
    peso_kg: 18000,
  },
];

beforeEach(() => {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "1", rol: "operador", patios: ["p1"] },
    token: "token",
    ready: true,
    setToken: vi.fn(),
    logout: vi.fn(),
  });
  vi.mocked(listPatios).mockResolvedValue(PATIOS);
  vi.mocked(obtenerMapaPatio).mockResolvedValue(MAPA);
  vi.mocked(listarContenedores).mockResolvedValue(PENDIENTES);
  vi.mocked(obtenerDetalleTira).mockResolvedValue(DETALLE);
  vi.mocked(sugerirUbicacion).mockResolvedValue({
    ubicacion_id: "u1",
    codigo: "A1-T1-R1-N1",
    costo: 1.5,
    tira_id: "t1",
    nivel: 1,
  });
  vi.mocked(crearMovimiento).mockReset();
});

describe("MapaPage", () => {
  it("pide solo los contenedores sin ubicacion del patio", async () => {
    render(<MapaPage />);
    expect(await screen.findByText("MSCU1234567")).toBeVisible();
    expect(listarContenedores).toHaveBeenCalledWith("token", {
      patio_id: "p1",
      sin_ubicacion: true,
    });
  });

  it("coloca el contenedor en la ubicacion sugerida", async () => {
    vi.mocked(crearMovimiento).mockResolvedValue({
      id: "m1",
      contenedor_id: "c9",
      ubicacion_destino_id: "u1",
      tipo: "ingreso",
    });
    const user = userEvent.setup();
    render(<MapaPage />);

    await user.click(await screen.findByRole("button", { name: /MSCU1234567/ }));
    await user.click(await screen.findByRole("gridcell"));
    await user.click(await screen.findByRole("button", { name: "Colocar aquí" }));

    expect(crearMovimiento).toHaveBeenCalledWith("token", {
      contenedor_id: "c9",
      ubicacion_destino_id: "u1",
      tipo: "ingreso",
      override_manual: false,
      score_sugerido: 1.5,
      score_elegido: 1.5,
    });
  });

  it("muestra el conflicto 409 y recarga el mapa", async () => {
    vi.mocked(crearMovimiento).mockRejectedValue(new ApiError(409, "Ubicación ya ocupada"));
    const user = userEvent.setup();
    render(<MapaPage />);

    await user.click(await screen.findByRole("button", { name: /MSCU1234567/ }));
    await user.click(await screen.findByRole("gridcell"));
    await user.click(await screen.findByRole("button", { name: "Colocar aquí" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Ubicación ya ocupada");
    expect(obtenerMapaPatio).toHaveBeenCalledTimes(2);
  });

  it("avisa cuando el patio no tiene punto de entrada y no pide sugerencia", async () => {
    vi.mocked(obtenerMapaPatio).mockResolvedValue({ ...MAPA, ubicacion_entrada_id: null });
    const user = userEvent.setup();
    render(<MapaPage />);

    await user.click(await screen.findByRole("button", { name: /MSCU1234567/ }));

    expect(sugerirUbicacion).not.toHaveBeenCalled();
    expect(
      await screen.findByText(
        "Este patio no tiene punto de entrada, así que no se puede sugerir una ubicación."
      )
    ).toBeVisible();
  });
});
