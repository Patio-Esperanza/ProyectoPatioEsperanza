"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { decodeTokenSafe, tiempoHastaExpiracion } from "./jwt";
import { refreshToken, registrarManejadorRefresh } from "./api";

export interface AuthUser {
  id: string;
  rol: string;
  patios: string[];
}

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  ready: boolean;
  tokenExpiresAt: number | null;
  proximaExpiracion: boolean;
  errorRefresh: boolean;
  renovarSesion: () => Promise<void>;
  setToken: (token: string) => void;
  logout: () => void;
}

const STORAGE_KEY = "patio_esperanza_token";

/** Cuánto antes de caducar se le avisa al usuario. */
const AVISO_ANTES_MS = 120_000;
/** Cuánto antes de caducar se intenta renovar en silencio. */
const RENUEVA_ANTES_MS = 30_000;
/**
 * Un token vencido por menos de esto todavía se acepta al cargar la página: el backend lo
 * renueva dentro de su ventana de gracia, así que cerrar la sesión aquí sería tirar una
 * sesión que aún se puede salvar.
 */
const GRACIA_AL_CARGAR_SEGUNDOS = -60;
/**
 * `setTimeout` guarda el retardo en 32 bits: cualquier valor mayor se desborda y el timer
 * dispara de inmediato. Un token con un `exp` absurdamente lejano provocaba entonces aviso
 * y renovación en bucle, así que el retardo se acota.
 */
const RETARDO_MAXIMO_MS = 2_147_483_647;

function retardoHasta(instante: number, antesDeMs: number): number {
  return Math.min(Math.max(0, instante - Date.now() - antesDeMs), RETARDO_MAXIMO_MS);
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [tokenExpiresAt, setTokenExpiresAt] = useState<number | null>(null);
  const [proximaExpiracion, setProximaExpiracion] = useState(false);
  const [errorRefresh, setErrorRefresh] = useState(false);
  const actual = useRef<string | null>(null);
  // Sube en cada setToken y en cada logout. Un refresh en vuelo compara contra el valor
  // que vio al arrancar: si ya cambió, su resultado llega tarde y se descarta. Sin esto un
  // refresh lento podía revivir la sesión después de que el usuario cerró sesión.
  const generacion = useRef(0);
  const pendiente = useRef<Promise<void> | null>(null);

  const setToken = useCallback((next: string) => {
    const payload = decodeTokenSafe(next);
    if (!payload) throw new Error("Token inválido");
    generacion.current += 1;
    pendiente.current = null;
    localStorage.setItem(STORAGE_KEY, next);
    actual.current = next;
    setTokenState(next);
    setTokenExpiresAt(payload.exp * 1000);
    setProximaExpiracion(false);
    setErrorRefresh(false);
  }, []);

  const logout = useCallback(() => {
    generacion.current += 1;
    pendiente.current = null;
    actual.current = null;
    localStorage.removeItem(STORAGE_KEY);
    setTokenState(null);
    setTokenExpiresAt(null);
    setProximaExpiracion(false);
    setErrorRefresh(false);
  }, []);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    const payload = stored ? decodeTokenSafe(stored) : null;
    if (stored && payload && tiempoHastaExpiracion(payload) >= GRACIA_AL_CARGAR_SEGUNDOS) {
      setToken(stored);
    } else {
      logout();
    }
    setReady(true);
  }, [setToken, logout]);

  const renovarSesion = useCallback((): Promise<void> => {
    // Varias peticiones pueden descubrir el token vencido a la vez; todas esperan el mismo
    // refresh en vez de disparar uno cada una.
    if (pendiente.current) return pendiente.current;
    const current = actual.current;
    const version = generacion.current;
    if (!current) return Promise.reject(new Error("No hay sesión activa"));
    const promesa = (async () => {
      try {
        const next = await refreshToken(current);
        if (generacion.current !== version) return;
        const payload = decodeTokenSafe(next);
        if (!payload) throw new Error("Token inválido");
        setToken(next);
      } catch (error) {
        if (generacion.current === version) {
          pendiente.current = null;
          setErrorRefresh(true);
          setProximaExpiracion(true);
        }
        throw error;
      }
    })();
    pendiente.current = promesa;
    return promesa;
  }, [setToken]);

  useEffect(() => registrarManejadorRefresh(renovarSesion), [renovarSesion]);

  useEffect(() => {
    if (tokenExpiresAt === null) return;
    const aviso = setTimeout(
      () => setProximaExpiracion(true),
      retardoHasta(tokenExpiresAt, AVISO_ANTES_MS)
    );
    const renueva = setTimeout(() => {
      void renovarSesion().catch(() => {});
    }, retardoHasta(tokenExpiresAt, RENUEVA_ANTES_MS));
    // Los navegadores frenan los timers de las pestañas en segundo plano, así que al
    // volver se revisa a mano: este es el caso real de dejar la laptop abierta y regresar.
    const alVolver = () => {
      if (
        document.visibilityState === "visible" &&
        Date.now() >= tokenExpiresAt - RENUEVA_ANTES_MS
      ) {
        void renovarSesion().catch(() => {});
      }
    };
    document.addEventListener("visibilitychange", alVolver);
    return () => {
      clearTimeout(aviso);
      clearTimeout(renueva);
      document.removeEventListener("visibilitychange", alVolver);
    };
  }, [tokenExpiresAt, renovarSesion]);

  const user = useMemo(() => {
    const payload = token ? decodeTokenSafe(token) : null;
    return payload ? { id: payload.sub, rol: payload.rol, patios: payload.patios } : null;
  }, [token]);

  const value = useMemo(
    () => ({
      user,
      token,
      ready,
      tokenExpiresAt,
      proximaExpiracion,
      errorRefresh,
      renovarSesion,
      setToken,
      logout,
    }),
    [
      user,
      token,
      ready,
      tokenExpiresAt,
      proximaExpiracion,
      errorRefresh,
      renovarSesion,
      setToken,
      logout,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
