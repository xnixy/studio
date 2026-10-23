import type { ReactNode } from "react";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, ApiError, bindAuthSessionHandlers } from "./api";
import { accountIdentityChanged, resetAccountClientState } from "./lib/accountSession";
import type { AuthResponse, User } from "./types";

interface AuthContextValue {
  accessToken: string | null;
  user: User | null;
  initialized: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    options?: { fullName?: string; turnstileToken?: string | null },
  ) => Promise<void>;
  logout: () => Promise<void>;
  updateUser: (user: User) => void;
  requireToken: () => string;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [initialized, setInitialized] = useState(false);
  const didRestore = useRef(false);
  const tokenRef = useRef<string | null>(null);
  const userIdRef = useRef<string | null>(null);
  tokenRef.current = accessToken;

  const applySession = useCallback(
    (session: AuthResponse) => {
      const nextUserId = session.user?.id ?? null;
      if (accountIdentityChanged(userIdRef.current, nextUserId)) {
        resetAccountClientState(queryClient);
      }
      userIdRef.current = nextUserId;
      setAccessToken(session.access_token);
      setUser(session.user);
    },
    [queryClient],
  );

  const clearSession = useCallback(() => {
    userIdRef.current = null;
    setAccessToken(null);
    setUser(null);
    resetAccountClientState(queryClient);
  }, [queryClient]);

  useEffect(() => {
    bindAuthSessionHandlers({
      getAccessToken: () => tokenRef.current,
      applySession,
      clearSession,
    });
    return () => bindAuthSessionHandlers(null);
  }, [applySession, clearSession]);

  useEffect(() => {
    if (didRestore.current) {
      return;
    }
    didRestore.current = true;

    api
      .refresh()
      .then((session) => {
        // 204 no-cookie → undefined body; treat as signed-out without error noise.
        if (!session?.access_token || !session.user) {
          setAccessToken(null);
          setUser(null);
          return;
        }
        applySession(session);
      })
      .catch((error) => {
        // Expired/invalid cookie still 401; only warn for unexpected failures.
        if (!(error instanceof ApiError) || (error.status !== 401 && error.status !== 403)) {
          console.warn("Session restore failed", error);
          // A cold load during a network blip says nothing about the cookie.
          // Leave the session alone; the next authenticated call re-checks.
          return;
        }
        setAccessToken(null);
        setUser(null);
        userIdRef.current = null;
      })
      .finally(() => setInitialized(true));
  }, [applySession]);

  const login = useCallback(async (email: string, password: string) => {
    const session = await api.login(email, password);
    resetAccountClientState(queryClient);
    applySession(session);
  }, [applySession, queryClient]);

  const register = useCallback(
    async (
      email: string,
      password: string,
      options?: { fullName?: string; turnstileToken?: string | null },
    ) => {
      const session = await api.register(email, password, options);
      resetAccountClientState(queryClient);
      applySession(session);
    },
    [applySession, queryClient],
  );

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const emailVerifiedRef = useRef(false);
  emailVerifiedRef.current = Boolean(user?.email_verified);

  const updateUser = useCallback(
    (nextUser: User) => {
      const wasVerified = emailVerifiedRef.current;
      setUser(nextUser);
      if (nextUser.email_verified && !wasVerified) {
        void queryClient.invalidateQueries({ queryKey: ["workspaces"] });
      }
    },
    [queryClient],
  );

  /**
   * Prefer for mutations / event handlers. Safe to call only when authenticated.
   * For render/query setup use `accessToken` + `enabled: Boolean(accessToken)`.
   */
  const requireToken = useCallback(() => {
    if (!accessToken) {
      throw new Error("Not authenticated");
    }
    return accessToken;
  }, [accessToken]);

  const value = useMemo<AuthContextValue>(
    () => ({
      accessToken,
      user,
      initialized,
      isAuthenticated: Boolean(user && accessToken),
      isAdmin: user?.role === "admin",
      login,
      register,
      logout,
      updateUser,
      requireToken,
    }),
    [accessToken, initialized, login, logout, register, requireToken, updateUser, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
