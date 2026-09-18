"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { decodeJwtPayload } from "./jwt";

export interface AuthUser {
  id: string;
  rol: string;
  patios: string[];
}

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  ready: boolean;
  setToken: (token: string) => void;
  logout: () => void;
}

const STORAGE_KEY = "patio_esperanza_token";

const AuthContext = createContext<AuthContextValue | null>(null);

function userFromToken(token: string): AuthUser {
  const payload = decodeJwtPayload(token);
  return { id: payload.sub, rol: payload.rol, patios: payload.patios };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      setTokenState(stored);
    }
    setReady(true);
  }, []);

  const setToken = useCallback((next: string) => {
    localStorage.setItem(STORAGE_KEY, next);
    setTokenState(next);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setTokenState(null);
  }, []);

  const user = useMemo(() => (token ? userFromToken(token) : null), [token]);

  const value = useMemo(
    () => ({ user, token, ready, setToken, logout }),
    [user, token, ready, setToken, logout]
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
