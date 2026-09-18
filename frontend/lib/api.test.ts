import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  login,
  ApiError,
  listPatios,
  createPatio,
  type Patio,
  createContenedor,
  getContenedor,
  type Contenedor,
} from "./api";

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

describe("listPatios", () => {
  it("sends the bearer token and returns the list", async () => {
    const patios: Patio[] = [{ id: "1", nombre: "Patio Norte", codigo: "PN", activo: true }];
    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => patios });

    const result = await listPatios("token-123");

    expect(result).toEqual(patios);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/patios");
    expect(options.headers.Authorization).toBe("Bearer token-123");
  });
});

describe("createPatio", () => {
  it("posts the payload as JSON with the bearer token", async () => {
    const creado: Patio = { id: "2", nombre: "Patio Sur", codigo: "PS", activo: true };
    fetchMock.mockResolvedValue({ ok: true, status: 201, json: async () => creado });

    const result = await createPatio("token-123", { nombre: "Patio Sur", codigo: "PS" });

    expect(result).toEqual(creado);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/patios");
    expect(options.method).toBe("POST");
    expect(options.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(options.body as string)).toEqual({ nombre: "Patio Sur", codigo: "PS" });
  });
});

const CONTENEDOR: Contenedor = {
  id: "c1",
  numero_contenedor: "CSQU3054383",
  tipo: "lleno",
  tamano: "40",
  patio_id: "p1",
  estado: "solicitud_ingreso",
  peso_kg: 18000,
};

describe("createContenedor", () => {
  it("posts the payload as JSON", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 201, json: async () => CONTENEDOR });

    const result = await createContenedor("token-123", {
      numero_contenedor: "CSQU3054383",
      tipo: "lleno",
      tamano: "40",
      patio_id: "p1",
      peso_kg: 18000,
    });

    expect(result).toEqual(CONTENEDOR);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/contenedores");
    expect(options.method).toBe("POST");
  });
});

describe("getContenedor", () => {
  it("gets a contenedor by id", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => CONTENEDOR });

    const result = await getContenedor("token-123", "c1");

    expect(result).toEqual(CONTENEDOR);
    const [url] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/contenedores/c1");
  });
});
