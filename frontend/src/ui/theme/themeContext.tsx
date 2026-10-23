import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { applyBrandCssVars, BRANDS } from "./brand";
import "../../styles/tailwind.css";

export type ThemePreference = "dark" | "light" | "system";
export type ResolvedTheme = "dark" | "light";

const STORAGE_KEY = "studio.theme";
const LEGACY_BRAND_KEY = "studio.brand";
const LEGACY_MATERIAL_KEY = "studio.material";
const LEGACY_PERF_KEY = "studio.perf";

type ThemeContextValue = {
  preference: ThemePreference;
  resolved: ResolvedTheme;
  setPreference: (theme: ThemePreference) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function fallbackThemeValue(): ThemeContextValue {
  const preference = readStoredPreference();
  return {
    preference,
    resolved: resolvePreference(preference),
    setPreference: () => {},
  };
}

function resolvePreference(preference: ThemePreference): ResolvedTheme {
  if (preference !== "system") return preference;
  if (typeof window === "undefined") return "dark";
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function readStoredPreference(): ThemePreference {
  if (typeof window === "undefined") return "system";
  const raw = localStorage.getItem(STORAGE_KEY) as ThemePreference | null;
  return raw === "light" || raw === "system" || raw === "dark" ? raw : "system";
}

function clearLegacyKeys() {
  try {
    localStorage.removeItem(LEGACY_BRAND_KEY);
    localStorage.removeItem(LEGACY_MATERIAL_KEY);
    localStorage.removeItem(LEGACY_PERF_KEY);
  } catch {
    /* ignore */
  }
}

function applyDomTheme(resolved: ResolvedTheme, preference: ThemePreference) {
  const root = document.documentElement;
  root.dataset.theme = resolved;
  root.dataset.brand = "black";
  delete root.dataset.material;
  delete root.dataset.materialRequested;
  delete root.dataset.perf;
  root.style.colorScheme = resolved;
  localStorage.setItem(STORAGE_KEY, preference);
  clearLegacyKeys();

  applyBrandCssVars(resolved);

  const metaBrand = BRANDS.black;
  const surface = resolved === "dark" ? metaBrand.darkSurface : metaBrand.lightSurface;
  const canvasBg = surface.bg1;

  if (document.body) {
    document.body.classList.remove("scene-bg", "studio-material-ambient");
    document.body.style.backgroundColor = canvasBg;
    document.body.style.color = surface.fg;
  }

  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", canvasBg);
}

export function StudioThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreferenceState] = useState<ThemePreference>(() => readStoredPreference());
  const [resolved, setResolved] = useState<ResolvedTheme>(() =>
    resolvePreference(readStoredPreference()),
  );

  const setPreference = useCallback((next: ThemePreference) => {
    setPreferenceState(next);
    const r = resolvePreference(next);
    setResolved(r);
    applyDomTheme(r, next);
  }, []);

  useEffect(() => {
    const r = resolvePreference(preference);
    setResolved(r);
    applyDomTheme(r, preference);

    const media = window.matchMedia("(prefers-color-scheme: light)");
    const onChange = () => {
      if (preference === "system") {
        const next = resolvePreference("system");
        setResolved(next);
        applyDomTheme(next, "system");
      }
    };
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [preference]);

  const value = useMemo(
    () => ({ preference, resolved, setPreference }),
    [preference, resolved, setPreference],
  );

  return (
    <ThemeContext.Provider value={value}>
      <div className="studio-app-root min-h-full bg-transparent text-[var(--studio-fg)]">
        {children}
        <div id="studio-portal-root" />
      </div>
    </ThemeContext.Provider>
  );
}

export function useStudioTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    if (import.meta.env.DEV) {
      console.warn("[Studio] useStudioTheme used outside StudioThemeProvider; using storage fallback");
    }
    return fallbackThemeValue();
  }
  return ctx;
}
