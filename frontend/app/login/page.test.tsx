import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LoginPage from "./page";
import { AuthProvider } from "@/lib/auth-context";
import { login, ApiError } from "@/lib/api";

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, login: vi.fn() };
});

const FAKE_PAYLOAD = { sub: "usr-1", rol: "admin", patios: [], iat: 0, exp: 9999999999 };
const FAKE_TOKEN = `${btoa("{}")}.${btoa(JSON.stringify(FAKE_PAYLOAD))}.sig`;

beforeEach(() => {
  localStorage.clear();
  pushMock.mockClear();
  vi.mocked(login).mockReset();
});

describe("LoginPage", () => {
  it("logs in and redirects to /patios", async () => {
    const user = userEvent.setup();
    vi.mocked(login).mockResolvedValue({ access_token: FAKE_TOKEN, token_type: "bearer" });

    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    await user.type(screen.getByLabelText("Correo"), "admin@patio.mx");
    await user.type(screen.getByLabelText("Contraseña"), "clave123");
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/patios"));
  });

  it("shows the backend error message on failed login", async () => {
    const user = userEvent.setup();
    vi.mocked(login).mockRejectedValue(new ApiError(401, "Credenciales inválidas"));

    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    await user.type(screen.getByLabelText("Correo"), "admin@patio.mx");
    await user.type(screen.getByLabelText("Contraseña"), "mala");
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Credenciales inválidas");
  });
});
