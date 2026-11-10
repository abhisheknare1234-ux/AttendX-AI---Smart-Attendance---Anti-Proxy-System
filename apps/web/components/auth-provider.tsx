"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api } from "@/lib/api";
import type { MeResponse, MfaChallenge, User } from "@/lib/types";

export type LoginOutcome =
  | { kind: "session"; user: User }
  | { kind: "mfa"; challenge: MfaChallenge };

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<LoginOutcome>;
  verifyMfa: (challengeToken: string, code: string) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const me = await api<MeResponse>("/auth/me");
      setUser(me.user);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const response = await api<MeResponse | MfaChallenge>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if ("mfa_required" in response) {
      return { kind: "mfa" as const, challenge: response };
    }
    setUser(response.user);
    setLoading(false);
    return { kind: "session" as const, user: response.user };
  }, []);

  const verifyMfa = useCallback(async (challengeToken: string, code: string) => {
    const me = await api<MeResponse>("/auth/mfa/verify", {
      method: "POST",
      body: JSON.stringify({ challenge_token: challengeToken, code }),
    });
    setUser(me.user);
    setLoading(false);
    return me.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {
      // The local session is cleared even if the server call fails.
    } finally {
      setUser(null);
      router.replace("/login");
    }
  }, [router]);

  const value = useMemo(
    () => ({ user, loading, login, verifyMfa, logout, refresh }),
    [user, loading, login, verifyMfa, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}

export function homeForRole(role: User["role"]): string {
  if (role === "admin") return "/admin";
  if (role === "teacher") return "/teacher";
  return "/student";
}
