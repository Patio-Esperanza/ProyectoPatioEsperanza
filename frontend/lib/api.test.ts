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
  listClientes,
  createCliente,
  type Cliente,
  registrarCliente,
  verificarCliente,
  solicitarContenedor,
  obtenerPin,
  verificarPin,
  listarContenedores,
  solicitarSalida,
  actualizarPatio,
} from "./api";

const fetchMock = vi.fn();

function jsonResponse(data: unknown) {
  return { ok: true, status: 200, json: async () => data };
}

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
    const patios: Patio[] = [{ id: "1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 }];
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
    const creado: Patio = { id: "2", nombre: "Patio Sur", codigo: "PS", activo: true, anticipacion_minima_horas: 24 };
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
  patios: [{ id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 }],
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

const CLIENTE: Cliente = {
  id: "cl1",
  razon_social: "Importadora Demo",
  rfc: "AAA010101AA1",
  tipo: "importador_exportador",
  activo: true,
};

describe("listClientes", () => {
  it("sends the bearer token and returns the list", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => [CLIENTE] });

    const result = await listClientes("token-123");

    expect(result).toEqual([CLIENTE]);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/clientes");
    expect(options.headers.Authorization).toBe("Bearer token-123");
  });
});

describe("createCliente", () => {
  it("posts the payload as JSON with the bearer token", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 201, json: async () => CLIENTE });

    const result = await createCliente("token-123", {
      razon_social: "Importadora Demo",
      rfc: "AAA010101AA1",
      tipo: "importador_exportador",
    });

    expect(result).toEqual(CLIENTE);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/clientes");
    expect(options.method).toBe("POST");
  });
});

describe("registrarCliente", () => {
  it("posts the payload without a bearer token", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({ detail: "Código de verificación enviado" }),
    });

    const result = await registrarCliente({
      nombre: "Juan",
      email: "juan@empresa.mx",
      password: "clave1234",
      rfc: "AAA010101AA1",
    });

    expect(result).toEqual({ detail: "Código de verificación enviado" });
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/clientes/registro");
    expect(options.headers.Authorization).toBeUndefined();
  });
});

describe("verificarCliente", () => {
  it("posts email and codigo", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ detail: "Cuenta activada" }),
    });

    const result = await verificarCliente({ email: "juan@empresa.mx", codigo: "123456" });

    expect(result).toEqual({ detail: "Cuenta activada" });
    const [url] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/clientes/verificar");
  });
});

describe("solicitarContenedor", () => {
  it("posts the payload as JSON with the bearer token", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 201, json: async () => CONTENEDOR });

    const result = await solicitarContenedor("token-123", {
      numero_contenedor: "CSQU3054383",
      tipo: "lleno",
      tamano: "40",
      peso_kg: 18000,
      fecha_estimada_retiro: "2026-10-01",
    });

    expect(result).toEqual(CONTENEDOR);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/contenedores/solicitar");
    expect(options.method).toBe("POST");
  });
});

describe("obtenerPin", () => {
  it("returns the pin for an authorized user", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ pin_confirmacion: "4821" })
    );

    const result = await obtenerPin("token", "c1");

    expect(result).toEqual({ pin_confirmacion: "4821" });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/contenedores/c1/pin",
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer token" }) })
    );
  });
});

describe("verificarPin", () => {
  it("posts numero_contenedor and pin", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        id: "c1",
        numero_contenedor: "CSQU3054383",
        tipo: "lleno",
        tamano: "40",
        patio_id: "p1",
        estado: "en_porteria",
        peso_kg: 18000,
      })
    );

    const result = await verificarPin("token", { numero_contenedor: "CSQU3054383", pin: "4821" });

    expect(result.estado).toBe("en_porteria");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/contenedores/verificar-pin",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ numero_contenedor: "CSQU3054383", pin: "4821" }),
      })
    );
  });
});

describe("listarContenedores", () => {
  it("requests without filters", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse([]));

    await listarContenedores("token");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/contenedores",
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer token" }) })
    );
  });

  it("requests with query filters", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse([]));

    await listarContenedores("token", { estado: "solicitud_salida", patio_id: "p1" });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/contenedores?estado=solicitud_salida&patio_id=p1",
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer token" }) })
    );
  });
});

describe("solicitarSalida", () => {
  it("posts fecha_deseada_salida", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        id: "c1",
        numero_contenedor: "CSQU3054383",
        tipo: "lleno",
        tamano: "40",
        patio_id: "p1",
        estado: "solicitud_salida",
        peso_kg: 18000,
      })
    );

    const result = await solicitarSalida("token", "c1", "2026-10-05T12:00:00Z");

    expect(result.estado).toBe("solicitud_salida");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/contenedores/c1/solicitar-salida",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ fecha_deseada_salida: "2026-10-05T12:00:00Z" }),
      })
    );
  });
});

describe("actualizarPatio", () => {
  it("patches anticipacion_minima_horas", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 48 })
    );

    const result = await actualizarPatio("token", "p1", 48);

    expect(result.anticipacion_minima_horas).toBe(48);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/patios/p1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ anticipacion_minima_horas: 48 }),
      })
    );
  });
});
