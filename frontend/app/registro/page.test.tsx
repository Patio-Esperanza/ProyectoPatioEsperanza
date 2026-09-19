import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RegistroPage from "./page";
import { registrarCliente, ApiError } from "@/lib/api";

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, registrarCliente: vi.fn() };
});

beforeEach(() => {
  pushMock.mockClear();
  vi.mocked(registrarCliente).mockReset();
});

describe("RegistroPage", () => {
  it("registers and redirects to the verify page with the email", async () => {
    const user = userEvent.setup();
    vi.mocked(registrarCliente).mockResolvedValue({ detail: "Código de verificación enviado" });

    render(<RegistroPage />);

    await user.type(screen.getByLabelText("Nombre"), "Juan");
    await user.type(screen.getByLabelText("Correo"), "juan@empresa.mx");
    await user.type(screen.getByLabelText("Contraseña"), "clave1234");
    await user.type(screen.getByLabelText("RFC de tu empresa"), "AAA010101AA1");
    await user.click(screen.getByRole("button", { name: "Registrarme" }));

    expect(registrarCliente).toHaveBeenCalledWith({
      nombre: "Juan",
      email: "juan@empresa.mx",
      password: "clave1234",
      rfc: "AAA010101AA1",
    });
    await waitFor(() =>
      expect(pushMock).toHaveBeenCalledWith("/registro/verificar?email=juan%40empresa.mx")
    );
  });

  it("shows the backend error message on failure", async () => {
    const user = userEvent.setup();
    vi.mocked(registrarCliente).mockRejectedValue(new ApiError(409, "Email ya registrado"));

    render(<RegistroPage />);

    await user.type(screen.getByLabelText("Nombre"), "Juan");
    await user.type(screen.getByLabelText("Correo"), "juan@empresa.mx");
    await user.type(screen.getByLabelText("Contraseña"), "clave1234");
    await user.type(screen.getByLabelText("RFC de tu empresa"), "AAA010101AA1");
    await user.click(screen.getByRole("button", { name: "Registrarme" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Email ya registrado");
  });
});
