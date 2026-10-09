import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AvisoSesionCaducada } from "./AvisoSesionCaducada";
import { useAuth } from "@/lib/auth-context";

vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));

function mockSesion(overrides: Partial<ReturnType<typeof useAuth>> = {}) {
  const valor = {
    user: { id: "1", rol: "admin", patios: [] },
    token: "token",
    ready: true,
    tokenExpiresAt: Date.now() + 90_000,
    proximaExpiracion: true,
    errorRefresh: false,
    renovarSesion: vi.fn().mockResolvedValue(undefined),
    setToken: vi.fn(),
    logout: vi.fn(),
    ...overrides,
  };
  vi.mocked(useAuth).mockReturnValue(valor);
  return valor;
}

beforeEach(() => {
  vi.mocked(useAuth).mockReset();
});

describe("AvisoSesionCaducada", () => {
  it("renders nothing while the session is not about to expire", () => {
    mockSesion({ proximaExpiracion: false });
    const { container } = render(<AvisoSesionCaducada />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the remaining seconds when the session is about to expire", () => {
    mockSesion({ tokenExpiresAt: Date.now() + 90_000 });
    render(<AvisoSesionCaducada />);

    expect(screen.getByRole("heading", { level: 2 })).toBeInTheDocument();
    expect(screen.getByText(/Tiempo restante: 9[01] s/)).toBeInTheDocument();
  });

  it("says the session already expired once the countdown reaches zero", () => {
    mockSesion({ tokenExpiresAt: Date.now() - 1_000 });
    render(<AvisoSesionCaducada />);

    expect(screen.getByText("Tu sesión ha caducado.")).toBeInTheDocument();
  });

  it("renews the session from the button", async () => {
    const { renovarSesion } = mockSesion();
    const user = userEvent.setup();
    render(<AvisoSesionCaducada />);

    await user.click(screen.getByRole("button", { name: "Renovar sesion" }));

    expect(renovarSesion).toHaveBeenCalled();
  });

  it("logs out from the button", async () => {
    const { logout } = mockSesion();
    const user = userEvent.setup();
    render(<AvisoSesionCaducada />);

    await user.click(screen.getByRole("button", { name: "Cerrar sesion" }));

    expect(logout).toHaveBeenCalled();
  });

  it("explains the failure when the automatic renewal did not work", () => {
    mockSesion({ errorRefresh: true });
    render(<AvisoSesionCaducada />);

    expect(screen.getByRole("alert")).toHaveTextContent(
      "No se pudo renovar la sesión automáticamente"
    );
  });

  it("keeps the renew button usable after a failed renewal", async () => {
    const renovarSesion = vi.fn().mockRejectedValue(new Error("red caída"));
    mockSesion({ errorRefresh: true, renovarSesion });
    const user = userEvent.setup();
    render(<AvisoSesionCaducada />);

    const boton = screen.getByRole("button", { name: "Renovar sesion" });
    await user.click(boton);

    expect(renovarSesion).toHaveBeenCalled();
    expect(boton).not.toBeDisabled();
  });
});
