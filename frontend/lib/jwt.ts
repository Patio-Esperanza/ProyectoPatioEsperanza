export interface JwtPayload {
  sub: string;
  rol: string;
  patios: string[];
  iat: number;
  exp: number;
}

export function decodeJwtPayload(token: string): JwtPayload {
  const base64Url = token.split(".")[1];
  const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
  const json = atob(base64);
  return JSON.parse(json) as JwtPayload;
}
