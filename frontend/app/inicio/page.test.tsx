import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import InicioPage from "./page";
import { useAuth } from "@/lib/auth-context";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));

describe("InicioPage", () => {
  it("explains that the role has no work screen yet", () => {
    vi.mocked(useAuth).mockReturnValue({
      tokenExpiresAt: null,
      proximaExpiracion: false,
      errorRefresh: false,
      renovarSesion: vi.fn(),
      user: { id: "1", rol: "operador_grua", patios: [] },
      token: "t",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    render(<InicioPage />);

    expect(screen.getByRole("heading", { name: /aún no tiene pantalla/i })).toBeInTheDocument();
    expect(screen.getByText(/operador_grua/)).toBeInTheDocument();
  });
});
