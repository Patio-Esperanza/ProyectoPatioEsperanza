import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { usePatiosDisponibles } from "./use-patios-disponibles";
import { useAuth } from "./auth-context";
import { listPatios } from "./api";

vi.mock("./auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("./api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api")>();
  return { ...actual, listPatios: vi.fn() };
});

const PATIOS = [
  { id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true },
  { id: "p2", nombre: "Patio Sur", codigo: "PS", activo: true },
];

beforeEach(() => {
  vi.mocked(listPatios).mockReset();
});

describe("usePatiosDisponibles", () => {
  it("returns all patios for an admin", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "admin", patios: [] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });
    vi.mocked(listPatios).mockResolvedValue(PATIOS);

    const { result } = renderHook(() => usePatiosDisponibles());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.patios).toEqual(PATIOS);
  });

  it("filters to only the user's assigned patios for non-admin roles", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "operador", patios: ["p2"] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });
    vi.mocked(listPatios).mockResolvedValue(PATIOS);

    const { result } = renderHook(() => usePatiosDisponibles());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.patios).toEqual([PATIOS[1]]);
  });
});
