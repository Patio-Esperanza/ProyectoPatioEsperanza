import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NavBar } from "./NavBar";
import { useAuth } from "@/lib/auth-context";

vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));

beforeEach(() => {
  vi.mocked(useAuth).mockReset();
});

describe("NavBar", () => {
  it("renders nothing when there is no session", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      token: null,
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });

    const { container } = render(<NavBar />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the role and calls logout on click", async () => {
    const logoutMock = vi.fn();
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "operador", patios: [] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: logoutMock,
    });

    const user = userEvent.setup();
    render(<NavBar />);

    expect(screen.getByText("operador")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Salir" }));
    expect(logoutMock).toHaveBeenCalled();
  });

  it("shows the Usuarios link only for admin", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "operador", patios: [] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });
    const { rerender } = render(<NavBar />);
    expect(screen.queryByText("Usuarios")).not.toBeInTheDocument();

    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "admin", patios: [] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });
    rerender(<NavBar />);
    expect(screen.getByText("Usuarios")).toBeInTheDocument();
  });
});
