import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider, useAuth } from "./auth-context";
import { refreshToken } from "./api";

vi.mock("./api", () => ({
  refreshToken: vi.fn(),
  registrarManejadorRefresh: vi.fn(() => () => {}),
}));

const FAKE_PAYLOAD = { sub: "usr-1", rol: "admin", patios: ["patio-1"], iat: 0, exp: 9999999999 };
const FAKE_TOKEN = `${btoa("{}")}.${btoa(JSON.stringify(FAKE_PAYLOAD))}.signature`;

/** Token firmado de mentiras que caduca dentro de `segundos` (negativo: ya caducó). */
function tokenCon(segundos: number): string {
  const ahora = Math.floor(Date.now() / 1000);
  const payload = {
    sub: "usr-1",
    rol: "admin",
    patios: ["patio-1"],
    iat: ahora - 10,
    exp: ahora + segundos,
  };
  return `${btoa("{}")}.${btoa(JSON.stringify(payload))}.signature`;
}

function TestConsumer() {
  const { user, proximaExpiracion, errorRefresh, setToken, logout } = useAuth();
  return (
    <div>
      <span data-testid="rol">{user?.rol ?? "sin-sesion"}</span>
      <span data-testid="aviso">{proximaExpiracion ? "si" : "no"}</span>
      <span data-testid="error">{errorRefresh ? "si" : "no"}</span>
      <button onClick={() => setToken(FAKE_TOKEN)}>login</button>
      <button onClick={logout}>logout</button>
    </div>
  );
}

function renderProvider() {
  return render(
    <AuthProvider>
      <TestConsumer />
    </AuthProvider>
  );
}

beforeEach(() => {
  localStorage.clear();
  vi.mocked(refreshToken).mockReset();
});

describe("AuthProvider", () => {
  it("starts with no user and updates after setToken", async () => {
    const user = userEvent.setup();
    renderProvider();

    expect(screen.getByTestId("rol").textContent).toBe("sin-sesion");

    await user.click(screen.getByText("login"));

    expect(screen.getByTestId("rol").textContent).toBe("admin");
    expect(localStorage.getItem("patio_esperanza_token")).toBe(FAKE_TOKEN);
  });

  it("restores the session from localStorage on mount", () => {
    localStorage.setItem("patio_esperanza_token", FAKE_TOKEN);

    renderProvider();

    expect(screen.getByTestId("rol").textContent).toBe("admin");
  });

  it("clears the session on logout", async () => {
    const user = userEvent.setup();
    localStorage.setItem("patio_esperanza_token", FAKE_TOKEN);
    renderProvider();

    await user.click(screen.getByText("logout"));

    expect(screen.getByTestId("rol").textContent).toBe("sin-sesion");
    expect(localStorage.getItem("patio_esperanza_token")).toBeNull();
  });
});

describe("AuthProvider on a stale or broken stored token", () => {
  it("drops a token that expired long ago instead of starting a dead session", () => {
    localStorage.setItem("patio_esperanza_token", tokenCon(-3600));

    renderProvider();

    expect(screen.getByTestId("rol").textContent).toBe("sin-sesion");
    expect(localStorage.getItem("patio_esperanza_token")).toBeNull();
  });

  it("keeps a token that just expired, because the backend still renews it", () => {
    localStorage.setItem("patio_esperanza_token", tokenCon(-5));

    renderProvider();

    expect(screen.getByTestId("rol").textContent).toBe("admin");
  });

  it("treats a corrupted token as no session instead of crashing the render", () => {
    localStorage.setItem("patio_esperanza_token", "esto-no-es-un-jwt");

    renderProvider();

    expect(screen.getByTestId("rol").textContent).toBe("sin-sesion");
    expect(localStorage.getItem("patio_esperanza_token")).toBeNull();
  });
});

describe("AuthProvider renewal timers", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("warns the user two minutes before the token expires", async () => {
    localStorage.setItem("patio_esperanza_token", tokenCon(300));
    renderProvider();

    expect(screen.getByTestId("aviso").textContent).toBe("no");

    await act(async () => {
      vi.advanceTimersByTime(181_000);
    });

    expect(screen.getByTestId("aviso").textContent).toBe("si");
    expect(refreshToken).not.toHaveBeenCalled();
  });

  it("renews the token silently thirty seconds before it expires", async () => {
    localStorage.setItem("patio_esperanza_token", tokenCon(300));
    vi.mocked(refreshToken).mockResolvedValue(tokenCon(14_400));
    renderProvider();

    await act(async () => {
      vi.advanceTimersByTime(271_000);
    });

    expect(refreshToken).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("rol").textContent).toBe("admin");
    expect(screen.getByTestId("error").textContent).toBe("no");
  });

  it("surfaces the warning and the error when the silent renewal fails", async () => {
    localStorage.setItem("patio_esperanza_token", tokenCon(300));
    vi.mocked(refreshToken).mockRejectedValue(new Error("red caída"));
    renderProvider();

    await act(async () => {
      vi.advanceTimersByTime(271_000);
    });

    expect(screen.getByTestId("error").textContent).toBe("si");
    expect(screen.getByTestId("aviso").textContent).toBe("si");
  });

  it("does not warn right away when the token expires very far in the future", async () => {
    // Un retardo mayor a 2^31-1 ms desborda setTimeout y dispararía el aviso al instante.
    localStorage.setItem("patio_esperanza_token", FAKE_TOKEN);
    renderProvider();

    await act(async () => {
      vi.advanceTimersByTime(5_000);
    });

    expect(screen.getByTestId("aviso").textContent).toBe("no");
    expect(refreshToken).not.toHaveBeenCalled();
  });

  it("does not revive the session when the renewal lands after a logout", async () => {
    localStorage.setItem("patio_esperanza_token", tokenCon(300));
    let resolver: (token: string) => void = () => {};
    vi.mocked(refreshToken).mockReturnValue(
      new Promise<string>((resolve) => {
        resolver = resolve;
      })
    );
    renderProvider();

    await act(async () => {
      vi.advanceTimersByTime(271_000);
    });
    expect(refreshToken).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByText("logout"));
    await act(async () => {
      resolver(tokenCon(14_400));
    });

    expect(screen.getByTestId("rol").textContent).toBe("sin-sesion");
    expect(localStorage.getItem("patio_esperanza_token")).toBeNull();
  });
});
