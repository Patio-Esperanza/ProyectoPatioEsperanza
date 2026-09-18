import { beforeEach, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider, useAuth } from "./auth-context";

const FAKE_PAYLOAD = { sub: "usr-1", rol: "admin", patios: ["patio-1"], iat: 0, exp: 9999999999 };
const FAKE_TOKEN = `${btoa("{}")}.${btoa(JSON.stringify(FAKE_PAYLOAD))}.signature`;

function TestConsumer() {
  const { user, setToken, logout } = useAuth();
  return (
    <div>
      <span data-testid="rol">{user?.rol ?? "sin-sesion"}</span>
      <button onClick={() => setToken(FAKE_TOKEN)}>login</button>
      <button onClick={logout}>logout</button>
    </div>
  );
}

beforeEach(() => {
  localStorage.clear();
});

describe("AuthProvider", () => {
  it("starts with no user and updates after setToken", async () => {
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    expect(screen.getByTestId("rol").textContent).toBe("sin-sesion");

    await user.click(screen.getByText("login"));

    expect(screen.getByTestId("rol").textContent).toBe("admin");
    expect(localStorage.getItem("patio_esperanza_token")).toBe(FAKE_TOKEN);
  });

  it("restores the session from localStorage on mount", () => {
    localStorage.setItem("patio_esperanza_token", FAKE_TOKEN);

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    expect(screen.getByTestId("rol").textContent).toBe("admin");
  });

  it("clears the session on logout", async () => {
    const user = userEvent.setup();
    localStorage.setItem("patio_esperanza_token", FAKE_TOKEN);
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await user.click(screen.getByText("logout"));

    expect(screen.getByTestId("rol").textContent).toBe("sin-sesion");
    expect(localStorage.getItem("patio_esperanza_token")).toBeNull();
  });
});
