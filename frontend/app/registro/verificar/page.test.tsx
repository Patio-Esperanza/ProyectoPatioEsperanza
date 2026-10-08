import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import VerificarPage from "./page";
import { verificarCliente, ApiError } from "@/lib/api";

// Los tests cambian los parámetros de la URL, así que el mock lee de una
// referencia mutable en lugar de devolver un valor fijo.
const navegacion = vi.hoisted(() => ({ params: new URLSearchParams() }));

vi.mock("next/navigation", () => ({
  useSearchParams: () => navegacion.params,
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, verificarCliente: vi.fn() };
});

beforeEach(() => {
  vi.mocked(verificarCliente).mockReset();
  navegacion.params = new URLSearchParams("email=juan%40empresa.mx");
});

describe("VerificarPage", () => {
  it("prefills the email from the query string and shows the success message", async () => {
    const user = userEvent.setup();
    vi.mocked(verificarCliente).mockResolvedValue({ detail: "Cuenta activada" });

    render(<VerificarPage />);

    expect(screen.getByLabelText("Correo")).toHaveValue("juan@empresa.mx");
    await user.type(screen.getByLabelText("Código de 6 dígitos"), "123456");
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    expect(verificarCliente).toHaveBeenCalledWith({ email: "juan@empresa.mx", codigo: "123456" });
    expect(await screen.findByText("Cuenta activada")).toBeInTheDocument();
  });

  it("prefills the code when the email button carries it in the query string", async () => {
    navegacion.params = new URLSearchParams("email=juan%40empresa.mx&codigo=074723");
    const user = userEvent.setup();
    vi.mocked(verificarCliente).mockResolvedValue({ detail: "Cuenta activada" });

    render(<VerificarPage />);

    expect(screen.getByLabelText("Código de 6 dígitos")).toHaveValue("074723");
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    expect(verificarCliente).toHaveBeenCalledWith({
      email: "juan@empresa.mx",
      codigo: "074723",
    });
  });

  it("shows the backend error message on failure", async () => {
    const user = userEvent.setup();
    vi.mocked(verificarCliente).mockRejectedValue(new ApiError(422, "Código incorrecto"));

    render(<VerificarPage />);

    await user.type(screen.getByLabelText("Código de 6 dígitos"), "000000");
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Código incorrecto");
  });
});
