import { render, screen } from "@testing-library/react";
import { vi, test, expect } from "vitest";
import ServiciosPage from "@/app/servicios/page";
import { useAuth } from "@/lib/auth-context";
import { ApiError, listarServicios } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));

vi.mock("@/lib/auth-context", () => ({
  useAuth: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    listarServicios: vi.fn().mockResolvedValue([]),
  };
});

test("ServiciosPage renders today services list", () => {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "1", rol: "cuadrilla", patios: [] },
    token: "token",
    ready: true,
    setToken: vi.fn(),
    logout: vi.fn(),
    tokenExpiresAt: null,
    proximaExpiracion: false,
    errorRefresh: false,
    renovarSesion: vi.fn(),
  });

  render(<ServiciosPage />);
  expect(screen.getByText(/servicios de hoy/i)).toBeInTheDocument();
});

test("shows the load error as an alert", async () => {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "1", rol: "cuadrilla", patios: [] },
    token: "token",
    ready: true,
    setToken: vi.fn(),
    logout: vi.fn(),
    tokenExpiresAt: null,
    proximaExpiracion: false,
    errorRefresh: false,
    renovarSesion: vi.fn(),
  });
  vi.mocked(listarServicios).mockRejectedValueOnce(new ApiError(500, "Fallo del servidor"));

  render(<ServiciosPage />);

  expect(await screen.findByRole("alert")).toHaveTextContent("Fallo del servidor");
});
