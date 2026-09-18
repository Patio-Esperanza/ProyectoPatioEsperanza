import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PatiosPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { listPatios, createPatio } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, listPatios: vi.fn(), createPatio: vi.fn() };
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
  vi.mocked(listPatios).mockReset();
  vi.mocked(createPatio).mockReset();
});

describe("PatiosPage", () => {
  it("lists the patios returned by the backend", async () => {
    mockAuth("operador");
    vi.mocked(listPatios).mockResolvedValue([
      { id: "1", nombre: "Patio Norte", codigo: "PN", activo: true },
    ]);

    render(<PatiosPage />);

    expect(await screen.findByText(/Patio Norte/)).toBeInTheDocument();
  });

  it("hides the create form for non-admin roles", async () => {
    mockAuth("operador");
    vi.mocked(listPatios).mockResolvedValue([]);

    render(<PatiosPage />);

    await waitFor(() => expect(listPatios).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: "Crear patio" })).not.toBeInTheDocument();
  });

  it("lets an admin create a patio and refreshes the list", async () => {
    mockAuth("admin");
    vi.mocked(listPatios)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([{ id: "2", nombre: "Patio Sur", codigo: "PS", activo: true }]);
    vi.mocked(createPatio).mockResolvedValue({
      id: "2",
      nombre: "Patio Sur",
      codigo: "PS",
      activo: true,
    });

    const user = userEvent.setup();
    render(<PatiosPage />);

    await screen.findByRole("button", { name: "Crear patio" });
    await user.type(screen.getByLabelText("Nombre"), "Patio Sur");
    await user.type(screen.getByLabelText("Código"), "PS");
    await user.click(screen.getByRole("button", { name: "Crear patio" }));

    expect(createPatio).toHaveBeenCalledWith("token", { nombre: "Patio Sur", codigo: "PS" });
    expect(await screen.findByText(/Patio Sur/)).toBeInTheDocument();
  });
});
