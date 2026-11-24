import { beforeEach, describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";
import HomePage from "./page";
import { useAuth } from "@/lib/auth-context";

const { replaceMock } = vi.hoisted(() => ({ replaceMock: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
}));

vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));

beforeEach(() => {
  replaceMock.mockClear();
  vi.mocked(useAuth).mockReset();
});

describe("HomePage", () => {
  it("redirects to /patios when authenticated as admin", () => {
    vi.mocked(useAuth).mockReturnValue({
      tokenExpiresAt: null,
      proximaExpiracion: false,
      errorRefresh: false,
      renovarSesion: vi.fn(),
      user: { id: "1", rol: "admin", patios: [] },
      token: "t",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    render(<HomePage />);

    expect(replaceMock).toHaveBeenCalledWith("/patios");
  });

  it("redirects to /mis-contenedores when authenticated as cliente", () => {
    vi.mocked(useAuth).mockReturnValue({
      tokenExpiresAt: null,
      proximaExpiracion: false,
      errorRefresh: false,
      renovarSesion: vi.fn(),
      user: { id: "1", rol: "cliente", patios: [] },
      token: "t",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    render(<HomePage />);

    expect(replaceMock).toHaveBeenCalledWith("/mis-contenedores");
  });

  it("redirects to /porteria when authenticated as guardia", () => {
    vi.mocked(useAuth).mockReturnValue({
      tokenExpiresAt: null,
      proximaExpiracion: false,
      errorRefresh: false,
      renovarSesion: vi.fn(),
      user: { id: "1", rol: "guardia", patios: [] },
      token: "t",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    render(<HomePage />);

    expect(replaceMock).toHaveBeenCalledWith("/porteria");
  });

  it("redirects to /login when not authenticated", () => {
    vi.mocked(useAuth).mockReturnValue({
      tokenExpiresAt: null,
      proximaExpiracion: false,
      errorRefresh: false,
      renovarSesion: vi.fn(),
      user: null,
      token: null,
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    render(<HomePage />);

    expect(replaceMock).toHaveBeenCalledWith("/login");
  });

  it("does nothing while the session is not ready", () => {
    vi.mocked(useAuth).mockReturnValue({
      tokenExpiresAt: null,
      proximaExpiracion: false,
      errorRefresh: false,
      renovarSesion: vi.fn(),
      user: null,
      token: null,
      ready: false,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    render(<HomePage />);

    expect(replaceMock).not.toHaveBeenCalled();
  });
});
