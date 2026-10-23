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
import { useQueryClient } from "@tanstack/react-query";
import { api, ApiError, bindAuthHandlers } from "../api/client";
import type { AuthResponse, User } from "../api/types";
import { setIapWorkspaceId } from "../iap/store";
import { unregisterPushBeforeLogout } from "../lib/pushToken";
import { alertInfo } from "../lib/alerts";
import { accountIdentityChanged } from "../workspace/resolveWorkspaceId";
import { sessionStorage } from "./storage";

type AuthContextValue = {
  user: User | null;
  accessToken: string | null;
  initialized: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (input: {
    email: string;
    password: string;
    fullName: string;
    turnstileToken?: string | null;
  }) => Promise<void>;
  logout: () => Promise<void>;
  updateUser: (user: User) => void;
  requireToken: () => string;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);
  const accessRef = useRef<string | null>(null);
  const refreshRef = useRef<string | null>(null);
  const userIdRef = useRef<string | null>(null);
  accessRef.current = accessToken;

  const persistWarned = useRef(false);

  const dropAccountCaches = useCallback(() => {
    qc.clear();
    setIapWorkspaceId(null);
  }, [qc]);

  const applySession = useCallback(async (session: AuthResponse) => {
    const nextUserId = session.user?.id ?? null;
    if (accountIdentityChanged(userIdRef.current, nextUserId)) {
      dropAccountCaches();
    }
    userIdRef.current = nextUserId;
    const access = session.access_token;
    const refresh = session.refresh_token ?? refreshRef.current;
    accessRef.current = access;
    if (refresh) refreshRef.current = refresh;
    // Set React state first so isAuthenticated flips before navigation / storage I/O.
    setAccessToken(access);
    setUser(session.user);
    try {
      await sessionStorage.setTokens(access, refresh);
    } catch (error) {
      // Never fail a successful API login because Keychain is flaky on iOS.
      console.warn("Could not persist session tokens", error);
      if (!__DEV__ && !persistWarned.current) {
        persistWarned.current = true;
        alertInfo(
          "Couldn't save sign-in",
          "You're signed in for now. If you close the app you may need to sign in again.",
        );
      }
    }
  }, [dropAccountCaches]);

  const beginNewAccountSession = useCallback(async () => {
    dropAccountCaches();
    try {
      await sessionStorage.clearAccountPrefs();
    } catch (error) {
      console.warn("Could not clear account prefs", error);
    }
  }, [dropAccountCaches]);

  const clearSession = useCallback(async () => {
    userIdRef.current = null;
    setAccessToken(null);
    setUser(null);
    accessRef.current = null;
    refreshRef.current = null;
    dropAccountCaches();
    try {
      await sessionStorage.clearTokens();
    } catch (error) {
      console.warn("Could not clear session tokens", error);
    }
  }, [dropAccountCaches]);

  useEffect(() => {
    bindAuthHandlers({
      getAccessToken: () => accessRef.current,
      getRefreshToken: () => refreshRef.current,
      applySession,
      clearSession,
    });
    return () => bindAuthHandlers(null);
  }, [applySession, clearSession]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [storedAccess, storedRefresh] = await Promise.all([
          sessionStorage.getAccessToken(),
          sessionStorage.getRefreshToken(),
        ]);
        refreshRef.current = storedRefresh;
        if (storedRefresh) {
          const session = await api.refresh(storedRefresh);
          if (!cancelled && session?.access_token && session.user) {
            await applySession(session);
            return;
          }
        } else if (storedAccess) {
          // Access only (should be rare); try /me then clear on failure.
          accessRef.current = storedAccess;
          setAccessToken(storedAccess);
          try {
            const me = await api.me(storedAccess);
            if (!cancelled) {
              userIdRef.current = me.user?.id ?? null;
              setUser(me.user);
            }
            return;
          } catch {
            if (!cancelled) await clearSession();
          }
        }
      } catch (error) {
        const rejected = error instanceof ApiError && (error.status === 401 || error.status === 403);
        if (!rejected) {
          // Cold start with no signal is not a dead session. Keep the stored
          // tokens; the next authenticated call retries the refresh.
          console.warn("Session restore failed", error);
        } else if (!cancelled) {
          await clearSession();
        }
      } finally {
        if (!cancelled) setInitialized(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [applySession, clearSession]);

  const login = useCallback(
    async (email: string, password: string) => {
      const session = await api.login(email.trim(), password);
      await beginNewAccountSession();
      await applySession(session);
    },
    [applySession, beginNewAccountSession],
  );

  const register = useCallback(
    async (input: {
      email: string;
      password: string;
      fullName: string;
      turnstileToken?: string | null;
    }) => {
      const session = await api.register(input);
      await beginNewAccountSession();
      await applySession(session);
    },
    [applySession, beginNewAccountSession],
  );

  const logout = useCallback(async () => {
    const refresh = refreshRef.current;
    try {
      await unregisterPushBeforeLogout();
      await api.logout(refresh);
    } catch {
      // Still clear local session.
    } finally {
      await clearSession();
    }
  }, [clearSession]);

  const emailVerifiedRef = useRef(false);
  emailVerifiedRef.current = Boolean(user?.email_verified);

  const updateUser = useCallback(
    (next: User) => {
      const wasVerified = emailVerifiedRef.current;
      setUser(next);
      if (next.email_verified && !wasVerified) {
        void qc.invalidateQueries({ queryKey: ["workspaces"] });
      }
    },
    [qc],
  );

  const requireToken = useCallback(() => {
    if (!accessToken) throw new Error("Not authenticated");
    return accessToken;
  }, [accessToken]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      accessToken,
      initialized,
      isAuthenticated: Boolean(user && accessToken),
      isAdmin: user?.role === "admin",
      login,
      register,
      logout,
      updateUser,
      requireToken,
    }),
    [user, accessToken, initialized, login, register, logout, updateUser, requireToken],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
