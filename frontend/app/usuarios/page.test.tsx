import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import UsuariosPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { listUsuarios, createUsuario, listPatios } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, listUsuarios: vi.fn(), createUsuario: vi.fn(), listPatios: vi.fn() };
});

function mockAuth(rol: string, patios: string[] = []) {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "1", rol, patios },
    token: "token",
    ready: true,
    setToken: vi.fn(),
    logout: vi.fn(),
  });
}

const PATIOS = [
  { id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 },
  { id: "p2", nombre: "Patio Sur", codigo: "PS", activo: true, anticipacion_minima_horas: 24 },
];

beforeEach(() => {
  vi.mocked(listUsuarios).mockReset();
  vi.mocked(createUsuario).mockReset();
  vi.mocked(listPatios).mockReset();
  vi.mocked(listPatios).mockResolvedValue(PATIOS);
});

describe("UsuariosPage", () => {
  it("shows a not-authorized message for non-admin roles", async () => {
    mockAuth("operador", ["p1"]);

    render(<UsuariosPage />);

    expect(
      await screen.findByRole("heading", { name: "No tienes permiso para ver esta página" })
    ).toBeInTheDocument();
    expect(listUsuarios).not.toHaveBeenCalled();
  });

  it("lists the usuarios returned by the backend for admin", async () => {
    mockAuth("admin");
    vi.mocked(listUsuarios).mockResolvedValue([
      {
        id: "u1",
        nombre: "Juan Operador",
        email: "juan@patio.mx",
        tipo: "operador",
        activo: true,
        patios: [{ id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 }],
      },
    ]);

    render(<UsuariosPage />);

    expect(await screen.findByText(/Juan Operador/)).toBeInTheDocument();
  });

  it("lets an admin create a usuario and refreshes the list", async () => {
    mockAuth("admin");
    vi.mocked(listUsuarios)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        {
          id: "u2",
          nombre: "Ana Supervisora",
          email: "ana@patio.mx",
          tipo: "supervisor",
          activo: true,
          patios: [{ id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 }],
        },
      ]);
    vi.mocked(createUsuario).mockResolvedValue({
      id: "u2",
      nombre: "Ana Supervisora",
      email: "ana@patio.mx",
      tipo: "supervisor",
      activo: true,
      patios: [{ id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 }],
    });

    const user = userEvent.setup();
    render(<UsuariosPage />);

    await screen.findByRole("button", { name: "Crear usuario" });
    await user.type(screen.getByLabelText("Nombre"), "Ana Supervisora");
    await user.type(screen.getByLabelText("Correo"), "ana@patio.mx");
    await user.type(screen.getByLabelText("Contraseña"), "clave1234");
    await user.selectOptions(screen.getByLabelText("Rol"), "supervisor");
    await user.click(screen.getByLabelText("Patio Norte (PN)"));
    await user.click(screen.getByRole("button", { name: "Crear usuario" }));

    expect(createUsuario).toHaveBeenCalledWith("token", {
      nombre: "Ana Supervisora",
      email: "ana@patio.mx",
      password: "clave1234",
      tipo: "supervisor",
      patio_ids: ["p1"],
    });
    expect(await screen.findByText(/Ana Supervisora/)).toBeInTheDocument();
  });
});
