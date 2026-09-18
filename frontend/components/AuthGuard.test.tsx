import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { AuthGuard } from "./AuthGuard";
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

describe("AuthGuard", () => {
  it("renders children when there is a session", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "admin", patios: [] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    render(
      <AuthGuard>
        <p>contenido protegido</p>
      </AuthGuard>
    );

    expect(screen.getByText("contenido protegido")).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("redirects to /login when there is no session", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      token: null,
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    render(
      <AuthGuard>
        <p>contenido protegido</p>
      </AuthGuard>
    );

    expect(screen.queryByText("contenido protegido")).not.toBeInTheDocument();
    expect(replaceMock).toHaveBeenCalledWith("/login");
  });

  it("renders nothing while the session is not ready yet", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      token: null,
      ready: false,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    const { container } = render(
      <AuthGuard>
        <p>contenido protegido</p>
      </AuthGuard>
    );

    expect(container).toBeEmptyDOMElement();
    expect(replaceMock).not.toHaveBeenCalled();
  });
});
