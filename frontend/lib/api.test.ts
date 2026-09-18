import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { login, ApiError } from "./api";

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

describe("login", () => {
  it("posts form-encoded credentials and returns the token", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ access_token: "abc.def.ghi", token_type: "bearer" }),
    });

    const result = await login("admin@patio.mx", "clave123");

    expect(result).toEqual({ access_token: "abc.def.ghi", token_type: "bearer" });
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/auth/login");
    expect(options.method).toBe("POST");
    expect((options.body as URLSearchParams).toString()).toBe(
      "username=admin%40patio.mx&password=clave123"
    );
  });

  it("throws ApiError with the backend detail on failure", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: async () => ({ detail: "Credenciales inválidas" }),
    });

    await expect(login("admin@patio.mx", "mala")).rejects.toThrow(ApiError);
    await expect(login("admin@patio.mx", "mala")).rejects.toThrow("Credenciales inválidas");
  });
});
