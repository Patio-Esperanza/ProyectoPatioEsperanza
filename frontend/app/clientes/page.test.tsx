import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ClientesPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { listClientes, createCliente } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, listClientes: vi.fn(), createCliente: vi.fn() };
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
  vi.mocked(listClientes).mockReset();
  vi.mocked(createCliente).mockReset();
});

describe("ClientesPage", () => {
  it("shows a not-authorized message for non-admin roles", async () => {
    mockAuth("operador");

    render(<ClientesPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("No autorizado");
    expect(listClientes).not.toHaveBeenCalled();
  });

  it("lists the clientes returned by the backend for admin", async () => {
    mockAuth("admin");
    vi.mocked(listClientes).mockResolvedValue([
      {
        id: "cl1",
        razon_social: "Importadora Demo",
        rfc: "AAA010101AA1",
        tipo: "importador_exportador",
        activo: true,
      },
    ]);

    render(<ClientesPage />);

    expect(await screen.findByText(/Importadora Demo/)).toBeInTheDocument();
  });

  it("lets an admin create a cliente and refreshes the list", async () => {
    mockAuth("admin");
    vi.mocked(listClientes)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        {
          id: "cl2",
          razon_social: "Transportes Demo",
          rfc: "AAA010101AA2",
          tipo: "transportista",
          activo: true,
        },
      ]);
    vi.mocked(createCliente).mockResolvedValue({
      id: "cl2",
      razon_social: "Transportes Demo",
      rfc: "AAA010101AA2",
      tipo: "transportista",
      activo: true,
    });

    const user = userEvent.setup();
    render(<ClientesPage />);

    await screen.findByRole("button", { name: "Crear cliente" });
    await user.type(screen.getByLabelText("Razón social"), "Transportes Demo");
    await user.type(screen.getByLabelText("RFC"), "AAA010101AA2");
    await user.selectOptions(screen.getByLabelText("Tipo"), "transportista");
    await user.click(screen.getByRole("button", { name: "Crear cliente" }));

    expect(createCliente).toHaveBeenCalledWith("token", {
      razon_social: "Transportes Demo",
      rfc: "AAA010101AA2",
      tipo: "transportista",
    });
    expect(await screen.findByText(/Transportes Demo/)).toBeInTheDocument();
  });
});
