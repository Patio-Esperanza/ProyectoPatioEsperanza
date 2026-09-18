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
  crearMovimiento,
  type Movimiento,
  sugerirUbicacion,
  type SugerenciaUbicacion,
  listUsuarios,
  createUsuario,
  type Usuario,
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

describe("crearMovimiento", () => {
  it("posts the payload and returns the movimiento", async () => {
    const movimiento: Movimiento = {
      id: "m1",
      contenedor_id: "c1",
      ubicacion_destino_id: "u1",
      tipo: "ingreso",
    };
    fetchMock.mockResolvedValue({ ok: true, status: 201, json: async () => movimiento });

    const result = await crearMovimiento("token-123", {
      contenedor_id: "c1",
      ubicacion_destino_id: "u1",
      tipo: "ingreso",
    });

    expect(result).toEqual(movimiento);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/movimientos");
    expect(options.method).toBe("POST");
  });
});

describe("sugerirUbicacion", () => {
  it("posts the payload and returns the suggestion", async () => {
    const sugerencia: SugerenciaUbicacion = {
      ubicacion_id: "u1",
      codigo: "A1-T1-S1-N1",
      costo: 1.3,
    };
    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => sugerencia });

    const result = await sugerirUbicacion("token-123", {
      patio_id: "p1",
      contenedor_id: "c1",
      punto_referencia_ubicacion_id: "u0",
    });

    expect(result).toEqual(sugerencia);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/ubicaciones/sugerir");
    expect(options.method).toBe("POST");
  });
});

const USUARIO: Usuario = {
  id: "u1",
  nombre: "Juan Operador",
  email: "juan@patio.mx",
  tipo: "operador",
  activo: true,
  patios: [{ id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true }],
};

describe("listUsuarios", () => {
  it("sends the bearer token and returns the list", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => [USUARIO] });

    const result = await listUsuarios("token-123");

    expect(result).toEqual([USUARIO]);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/usuarios");
    expect(options.headers.Authorization).toBe("Bearer token-123");
  });
});

describe("createUsuario", () => {
  it("posts the payload as JSON with the bearer token", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 201, json: async () => USUARIO });

    const result = await createUsuario("token-123", {
      nombre: "Juan Operador",
      email: "juan@patio.mx",
      password: "clave1234",
      tipo: "operador",
      patio_ids: ["p1"],
    });

    expect(result).toEqual(USUARIO);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/usuarios");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body as string)).toEqual({
      nombre: "Juan Operador",
      email: "juan@patio.mx",
      password: "clave1234",
      tipo: "operador",
      patio_ids: ["p1"],
    });
  });
});
