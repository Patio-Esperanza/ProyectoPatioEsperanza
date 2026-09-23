const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit & { token?: string } = {}
): Promise<T> {
  const { token, headers, body, ...rest } = options;
  const isFormBody = body instanceof URLSearchParams;

  const response = await fetch(`${API_URL}${path}`, {
    ...rest,
    body,
    headers: {
      ...(body && !isFormBody ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const errorBody = await response.json();
      detail = errorBody.detail ?? detail;
    } catch {
      // sin cuerpo JSON en la respuesta de error
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export async function login(username: string, password: string): Promise<TokenResponse> {
  const body = new URLSearchParams({ username, password });
  return request<TokenResponse>("/api/auth/login", { method: "POST", body });
}

export interface Patio {
  id: string;
  nombre: string;
  codigo: string;
  activo: boolean;
  anticipacion_minima_horas: number;
}

export async function listPatios(token: string): Promise<Patio[]> {
  return request<Patio[]>("/api/patios", { token });
}

export async function actualizarPatio(
  token: string,
  id: string,
  anticipacion_minima_horas: number
): Promise<Patio> {
  return request<Patio>(`/api/patios/${id}`, {
    method: "PATCH",
    token,
    body: JSON.stringify({ anticipacion_minima_horas }),
  });
}

export async function createPatio(
  token: string,
  payload: { nombre: string; codigo: string }
): Promise<Patio> {
  return request<Patio>("/api/patios", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export type TipoContenedor = "lleno" | "vacio";
export type TamanoContenedor = "20" | "40" | "45";
export type EstadoContenedor =
  | "solicitud_ingreso"
  | "qr_ingreso_emitido"
  | "en_porteria"
  | "ingresado"
  | "ubicado"
  | "en_estadia"
  | "en_servicio_especial"
  | "solicitud_salida"
  | "qr_salida_emitido"
  | "en_porteria_salida"
  | "despachado"
  | "rechazado";

export interface Contenedor {
  id: string;
  numero_contenedor: string;
  tipo: TipoContenedor;
  tamano: TamanoContenedor;
  patio_id: string;
  estado: EstadoContenedor;
  peso_kg: number;
  fecha_estimada_retiro?: string | null;
  fecha_deseada_salida?: string | null;
}

export async function createContenedor(
  token: string,
  payload: {
    numero_contenedor: string;
    tipo: TipoContenedor;
    tamano: TamanoContenedor;
    patio_id: string;
    peso_kg: number;
  }
): Promise<Contenedor> {
  return request<Contenedor>("/api/contenedores", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function getContenedor(token: string, id: string): Promise<Contenedor> {
  return request<Contenedor>(`/api/contenedores/${id}`, { token });
}

export async function listarContenedores(
  token: string,
  filtros?: {
    estado?: EstadoContenedor;
    patio_id?: string;
    cliente_id?: string;
    sin_ubicacion?: boolean;
  }
): Promise<Contenedor[]> {
  const params = new URLSearchParams();
  if (filtros?.estado) params.set("estado", filtros.estado);
  if (filtros?.patio_id) params.set("patio_id", filtros.patio_id);
  if (filtros?.cliente_id) params.set("cliente_id", filtros.cliente_id);
  if (filtros?.sin_ubicacion) params.set("sin_ubicacion", "true");
  const query = params.toString();
  return request<Contenedor[]>(`/api/contenedores${query ? `?${query}` : ""}`, { token });
}

export async function solicitarSalida(
  token: string,
  id: string,
  fecha_deseada_salida: string
): Promise<Contenedor> {
  return request<Contenedor>(`/api/contenedores/${id}/solicitar-salida`, {
    method: "POST",
    token,
    body: JSON.stringify({ fecha_deseada_salida }),
  });
}

export async function obtenerPin(token: string, id: string): Promise<{ pin_confirmacion: string }> {
  return request<{ pin_confirmacion: string }>(`/api/contenedores/${id}/pin`, { token });
}

export async function verificarPin(
  token: string,
  payload: { numero_contenedor: string; pin: string }
): Promise<Contenedor> {
  return request<Contenedor>("/api/contenedores/verificar-pin", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export type TipoMovimiento = "ingreso" | "reubicacion" | "servicio" | "salida";

export interface Movimiento {
  id: string;
  contenedor_id: string;
  ubicacion_destino_id: string | null;
  tipo: TipoMovimiento;
}

export async function crearMovimiento(
  token: string,
  payload: {
    contenedor_id: string;
    ubicacion_destino_id: string;
    tipo: TipoMovimiento;
    override_manual?: boolean;
    motivo_override?: string;
    score_sugerido?: number;
    score_elegido?: number;
  }
): Promise<Movimiento> {
  return request<Movimiento>("/api/movimientos", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export interface SugerenciaUbicacion {
  ubicacion_id: string;
  codigo: string;
  costo: number;
  tira_id: string;
  nivel: number;
}

export async function sugerirUbicacion(
  token: string,
  payload: { patio_id: string; contenedor_id: string; punto_referencia_ubicacion_id: string }
): Promise<SugerenciaUbicacion> {
  return request<SugerenciaUbicacion>("/api/ubicaciones/sugerir", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export type RolUsuario = "operador" | "supervisor" | "admin" | "guardia" | "despachador";

export interface Usuario {
  id: string;
  nombre: string | null;
  email: string;
  tipo: RolUsuario;
  activo: boolean;
  patios: Patio[];
}

export async function listUsuarios(token: string): Promise<Usuario[]> {
  return request<Usuario[]>("/api/usuarios", { token });
}

export async function createUsuario(
  token: string,
  payload: {
    nombre: string;
    email: string;
    password: string;
    tipo: RolUsuario;
    patio_ids: string[];
  }
): Promise<Usuario> {
  return request<Usuario>("/api/usuarios", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export type TipoCliente =
  | "agencia_aduanal"
  | "importador_exportador"
  | "transportista"
  | "socio_api";

export interface Cliente {
  id: string;
  razon_social: string;
  rfc: string;
  tipo: TipoCliente;
  activo: boolean;
}

export async function listClientes(token: string): Promise<Cliente[]> {
  return request<Cliente[]>("/api/clientes", { token });
}

export async function createCliente(
  token: string,
  payload: { razon_social: string; rfc: string; tipo: TipoCliente }
): Promise<Cliente> {
  return request<Cliente>("/api/clientes", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function registrarCliente(payload: {
  nombre: string;
  email: string;
  password: string;
  rfc: string;
}): Promise<{ detail: string }> {
  return request<{ detail: string }>("/api/clientes/registro", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function verificarCliente(payload: {
  email: string;
  codigo: string;
}): Promise<{ detail: string }> {
  return request<{ detail: string }>("/api/clientes/verificar", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function solicitarContenedor(
  token: string,
  payload: {
    numero_contenedor: string;
    tipo: TipoContenedor;
    tamano: TamanoContenedor;
    peso_kg: number;
    fecha_estimada_retiro?: string;
  }
): Promise<Contenedor> {
  return request<Contenedor>("/api/contenedores/solicitar", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export interface TiraMapa {
  id: string;
  codigo: string;
  orden: number;
  niveles_totales: number;
  niveles_activos: number;
  niveles_ocupados: number;
}

export interface TramoMapa {
  id: string;
  codigo: string;
  orden: number;
  tiras: TiraMapa[];
}

export interface CarrilMapa {
  id: string;
  codigo: string;
  orden: number;
  tipo_teorico: TipoContenedor | null;
  tramos: TramoMapa[];
}

export interface MapaPatio {
  patio_id: string;
  ubicacion_entrada_id: string | null;
  resumen: { ubicaciones_activas: number; ocupadas: number };
  carriles: CarrilMapa[];
}

export interface ContenedorEnNivel {
  id: string;
  numero_contenedor: string;
  tipo: TipoContenedor;
  tamano: TamanoContenedor;
  peso_kg: number;
  estado: EstadoContenedor;
}

export interface NivelTira {
  nivel: number;
  ubicacion_id: string;
  codigo: string;
  activo: boolean;
  capacidad_peso_kg: number;
  contenedor: ContenedorEnNivel | null;
}

export interface DetalleTira {
  tira_id: string;
  codigo: string;
  niveles: NivelTira[];
}

export async function obtenerMapaPatio(token: string, patioId: string): Promise<MapaPatio> {
  return request<MapaPatio>(`/api/patios/${patioId}/mapa`, { token });
}

export async function obtenerDetalleTira(token: string, tiraId: string): Promise<DetalleTira> {
  return request<DetalleTira>(`/api/tiras/${tiraId}`, { token });
}
