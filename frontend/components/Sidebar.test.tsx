import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Sidebar } from "./Sidebar";
import { useAuth } from "@/lib/auth-context";

const { replaceMock, pathnameMock } = vi.hoisted(() => ({
  replaceMock: vi.fn(),
  pathnameMock: vi.fn(() => "/contenedores"),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
  usePathname: () => pathnameMock(),
}));

vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));

function mockSession(rol: string, logout = vi.fn()) {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "1", rol, patios: [] },
    token: "token",
    ready: true,
    setToken: vi.fn(),
    logout,
  });
  return logout;
}

beforeEach(() => {
  replaceMock.mockClear();
  pathnameMock.mockReturnValue("/contenedores");
  vi.mocked(useAuth).mockReset();
});

describe("Sidebar", () => {
  it("renders nothing when there is no session", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      token: null,
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    const { container } = render(<Sidebar />);
    expect(container).toBeEmptyDOMElement();
  });

  it("groups the staff routes under their sections for an admin", () => {
    mockSession("admin");
    render(<Sidebar />);

    expect(screen.getByRole("heading", { name: "Operación" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Administración" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Usuarios" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Clientes" })).toBeInTheDocument();
  });

  it("hides the whole Cliente section from staff", () => {
    mockSession("operador");
    render(<Sidebar />);

    expect(screen.queryByRole("heading", { name: "Cliente" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Mis contenedores" })).not.toBeInTheDocument();
  });

  it("shows a cliente only its own section", () => {
    mockSession("cliente");
    render(<Sidebar />);

    expect(screen.getByRole("link", { name: "Mis contenedores" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Solicitar entrada" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Operación" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Patios" })).not.toBeInTheDocument();
  });

  it("hides the admin-only routes from an operador", () => {
    mockSession("operador");
    render(<Sidebar />);

    expect(screen.queryByRole("link", { name: "Usuarios" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Clientes" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Portería" })).toBeInTheDocument();
  });

  it("marks the current route with aria-current", () => {
    mockSession("admin");
    render(<Sidebar />);

    expect(screen.getByRole("link", { name: "Contenedores" })).toHaveAttribute(
      "aria-current",
      "page"
    );
    expect(screen.getByRole("link", { name: "Movimientos" })).not.toHaveAttribute(
      "aria-current"
    );
  });

  it("marks the parent route as current on a nested path", () => {
    mockSession("admin");
    pathnameMock.mockReturnValue("/contenedores/abc-123");
    render(<Sidebar />);

    expect(screen.getByRole("link", { name: "Contenedores" })).toHaveAttribute(
      "aria-current",
      "page"
    );
  });

  it("logs out and navigates to /login", async () => {
    const logout = mockSession("operador");
    const user = userEvent.setup();
    render(<Sidebar />);

    await user.click(screen.getByRole("button", { name: "Salir" }));

    expect(logout).toHaveBeenCalled();
    expect(replaceMock).toHaveBeenCalledWith("/login");
  });

  it("toggles the mobile drawer from the menu button", async () => {
    mockSession("operador");
    const user = userEvent.setup();
    render(<Sidebar />);

    const disparador = screen.getByRole("button", { name: "Abrir menú" });
    expect(disparador).toHaveAttribute("aria-expanded", "false");

    await user.click(disparador);

    expect(screen.getByRole("button", { name: "Cerrar menú" })).toHaveAttribute(
      "aria-expanded",
      "true"
    );
  });
});
