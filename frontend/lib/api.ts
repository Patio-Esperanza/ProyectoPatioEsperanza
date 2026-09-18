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
}

export async function listPatios(token: string): Promise<Patio[]> {
  return request<Patio[]>("/api/patios", { token });
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
