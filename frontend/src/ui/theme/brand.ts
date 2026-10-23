/**
 * Product palette aligned with the iOS app: ambient canvas, frosted glass panels,
 * system blue accent. Surfaces use translucent glass + blur, not flat solid slabs.
 */

const FONT_BASE =
  '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI Variable", "Segoe UI", system-ui, sans-serif';

/** Match iOS system blue (dark / light). */
export const ACCENT_DARK = "#0A84FF";
export const ACCENT_DARK_HOVER = "#409CFF";
export const ACCENT_LIGHT = "#007AFF";
export const ACCENT_LIGHT_HOVER = "#0066D6";
export const RGB_DARK = "10 132 255";
export const RGB_LIGHT = "0 122 255";

type Surface = { bg1: string; bg2: string; bg3: string; fg: string; fg2: string; fg3: string };

/** Ambient canvas (matches mobile theme.ts). */
const darkSurface: Surface = {
  bg1: "#050508",
  bg2: "#121214",
  bg3: "#1C1C1E",
  fg: "#F5F5F7",
  fg2: "#AEAEB2",
  fg3: "#8E8E93",
};

const lightSurface: Surface = {
  bg1: "#E8ECF4",
  bg2: "#F2F4F8",
  bg3: "#FFFFFF",
  fg: "#0B0B0F",
  fg2: "#3A3A3C",
  fg3: "#636366",
};

/** Brand ramp metadata (for docs / tools). Runtime paint uses applyBrandCssVars. */
export const studioBrand = {
  accentDark: ACCENT_DARK,
  accentLight: ACCENT_LIGHT,
  rgbDark: RGB_DARK,
  rgbLight: RGB_LIGHT,
  fontFamily: FONT_BASE,
} as const;

/**
 * Apply brand/mode CSS custom properties.
 * Glass material: translucent panels + backdrop blur (iOS liquid-glass vibe).
 */
export function applyBrandCssVars(mode: "light" | "dark") {
  const root = document.documentElement;
  const isDark = mode === "dark";
  const s = isDark ? darkSurface : lightSurface;
  const rgb = isDark ? RGB_DARK : RGB_LIGHT;
  const primary = isDark ? ACCENT_DARK : ACCENT_LIGHT;
  const hover = isDark ? ACCENT_DARK_HOVER : ACCENT_LIGHT_HOVER;
  const onBrand = "#ffffff";

  const bg1 = s.bg1;
  const bg2 = s.bg2;
  const bg3 = s.bg3;

  const border = isDark ? "rgba(255, 255, 255, 0.12)" : "rgba(0, 0, 0, 0.08)";
  const borderSoft = isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.06)";
  const colorBorder = border;
  const colorBorderStrong = isDark ? "rgba(255, 255, 255, 0.18)" : "rgba(0, 0, 0, 0.12)";

  // Frosted panels (readable on ambient canvas).
  const panel = isDark ? "rgba(28, 28, 30, 0.72)" : "rgba(255, 255, 255, 0.72)";
  const panelSolid = isDark ? "#1C1C1E" : "#FFFFFF";
  const panelSoft = isDark ? "rgba(44, 44, 46, 0.55)" : "rgba(255, 255, 255, 0.55)";
  const elevated = isDark ? "rgba(44, 44, 46, 0.82)" : "rgba(255, 255, 255, 0.88)";
  const glass = panel;
  const glassStrong = isDark ? "rgba(28, 28, 30, 0.88)" : "rgba(255, 255, 255, 0.88)";

  // Neutral fills (iOS system greys). Soft chips, not solid paint.
  const fill = isDark ? "rgba(120, 120, 128, 0.28)" : "rgba(120, 120, 128, 0.16)";
  const fillSoft = isDark ? "rgba(120, 120, 128, 0.18)" : "rgba(120, 120, 128, 0.1)";
  const fillQuiet = isDark ? "rgba(120, 120, 128, 0.12)" : "rgba(120, 120, 128, 0.06)";

  root.dataset.brand = "ios-glass";
  root.dataset.material = "glass";
  delete root.dataset.materialRequested;
  delete root.dataset.perf;

  root.style.setProperty("--studio-brand-rgb", rgb);
  root.style.setProperty("--studio-brand", primary);
  root.style.setProperty("--studio-brand-hover", hover);
  root.style.setProperty("--studio-brand-fg", onBrand);

  root.style.setProperty("--studio-bg", bg1);
  root.style.setProperty("--studio-bg-2", bg2);
  root.style.setProperty("--studio-bg-3", bg3);
  root.style.setProperty("--studio-card", panel);
  root.style.setProperty("--studio-fg", s.fg);
  root.style.setProperty("--studio-fg-muted", s.fg2);
  root.style.setProperty("--studio-fg-subtle", s.fg3);
  root.style.setProperty("--studio-border", border);
  root.style.setProperty("--studio-border-soft", borderSoft);

  root.style.setProperty("--studio-fill", fill);
  root.style.setProperty("--studio-fill-soft", fillSoft);
  root.style.setProperty("--studio-fill-quiet", fillQuiet);

  root.style.setProperty("--studio-glass", glass);
  root.style.setProperty("--studio-glass-strong", glassStrong);
  root.style.setProperty("--studio-panel", panel);
  root.style.setProperty("--studio-panel-solid", panelSolid);
  root.style.setProperty("--studio-panel-soft", panelSoft);
  root.style.setProperty("--studio-elevated", elevated);

  // Soft float shadows (match mobile GlassCard)
  root.style.setProperty(
    "--studio-shadow-lg",
    isDark ? "0 20px 48px rgba(0,0,0,0.55)" : "0 16px 40px rgba(0,0,0,0.1)",
  );
  root.style.setProperty(
    "--studio-shadow",
    isDark ? "0 8px 24px rgba(0,0,0,0.4)" : "0 6px 20px rgba(0,0,0,0.08)",
  );
  root.style.setProperty("--studio-inset-tint", fillQuiet);
  root.style.setProperty("--studio-swatch-ring", isDark ? `rgb(${rgb} / 0.4)` : "rgba(0,0,0,0.12)");

  // Ambient orbs for glass to pick up (CSS radial layers on body)
  root.style.setProperty(
    "--studio-orb-a",
    isDark ? "rgba(10, 132, 255, 0.26)" : "rgba(0, 122, 255, 0.18)",
  );
  root.style.setProperty(
    "--studio-orb-b",
    isDark ? "rgba(175, 82, 222, 0.16)" : "rgba(175, 82, 222, 0.12)",
  );
  root.style.setProperty(
    "--studio-orb-c",
    isDark ? "rgba(48, 209, 88, 0.1)" : "rgba(52, 199, 89, 0.1)",
  );
  root.style.setProperty("--scene-glow", isDark ? "rgba(10, 132, 255, 0.12)" : "rgba(0, 122, 255, 0.08)");
  root.style.setProperty("--scene-glow-warm", isDark ? "rgba(175, 82, 222, 0.1)" : "rgba(175, 82, 222, 0.08)");

  const edge = isDark
    ? "inset 0 1px 0 rgba(255,255,255,0.12)"
    : "inset 0 1px 0 rgba(255,255,255,0.85)";
  root.style.setProperty("--studio-surface-border", border);
  root.style.setProperty("--studio-surface-highlight", edge);
  root.style.setProperty("--studio-shell-bg", bg1);
  root.style.setProperty("--studio-shell-bg-2", bg2);
  root.style.setProperty("--studio-shell-border", `1px solid ${border}`);
  root.style.setProperty("--studio-shell-fill", panel);
  root.style.setProperty("--studio-shell-fill-soft", panelSoft);
  root.style.setProperty("--studio-shell-wash", "none");
  root.style.setProperty("--studio-shell-wash-soft", "none");
  root.style.setProperty("--studio-shell-shadow", `${edge}, var(--studio-shadow)`);
  root.style.setProperty("--studio-shell-shadow-sm", edge);
  root.style.setProperty("--studio-card-bg", panel);
  root.style.setProperty("--studio-card-border", `1px solid ${border}`);
  root.style.setProperty("--studio-card-shadow", `${edge}, var(--studio-shadow)`);
  root.style.setProperty("--studio-card-radius", "22px");
  root.style.setProperty("--studio-material-blur", "28px");
  root.style.setProperty(
    "--studio-backdrop-filter",
    "blur(28px) saturate(1.35)",
  );
  root.style.setProperty("--studio-wallpaper-opacity", "0");
  root.style.setProperty("--studio-wallpaper-image", "none");
  root.style.setProperty("--studio-wallpaper-filter", "none");
  root.style.setProperty("--studio-wallpaper-brand-wash", "0");

  // Chat bubbles (iMessage)
  root.style.setProperty("--studio-bubble-user", primary);
  root.style.setProperty("--studio-bubble-user-fg", "#ffffff");
  root.style.setProperty(
    "--studio-bubble-system",
    isDark ? "rgba(118, 118, 128, 0.28)" : "rgba(120, 120, 128, 0.16)",
  );
  root.style.setProperty("--studio-bubble-system-fg", s.fg);
  root.style.setProperty(
    "--studio-chip-on",
    isDark ? "rgba(10, 132, 255, 0.28)" : "rgba(0, 122, 255, 0.14)",
  );
  root.style.setProperty(
    "--studio-chip-off",
    isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.05)",
  );

  root.style.setProperty("--color-bg", bg1);
  root.style.setProperty("--color-bg-subtle", bg2);
  root.style.setProperty("--color-bg-elevated", elevated);
  root.style.setProperty("--color-bg-sunken", isDark ? "#000000" : bg1);
  root.style.setProperty("--color-muted-surface", fillSoft);
  root.style.setProperty("--surface-bg", panel);
  root.style.setProperty("--surface-bg-solid", panelSolid);
  root.style.setProperty("--surface-border", border);
  root.style.setProperty(
    "--input-bg",
    isDark ? "rgba(118, 118, 128, 0.24)" : "rgba(120, 120, 128, 0.12)",
  );
  root.style.setProperty("--input-border", isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.08)");
  root.style.setProperty("--color-border", colorBorder);
  root.style.setProperty("--color-border-strong", colorBorderStrong);

  root.style.setProperty("--color-fg", s.fg);
  root.style.setProperty("--color-fg-muted", s.fg2);
  root.style.setProperty("--color-fg-subtle", s.fg3);
  root.style.setProperty("--color-muted", s.fg2);
  root.style.setProperty("--color-accent", primary);
  root.style.setProperty("--color-accent-hover", hover);
  root.style.setProperty("--color-accent-muted", `rgb(${rgb} / 0.14)`);
  root.style.setProperty("--color-accent-border", `rgb(${rgb} / 0.35)`);
  root.style.setProperty("--color-accent-fg", onBrand);
  root.style.setProperty("--color-primary", primary);
  root.style.setProperty("--color-primary-hover", hover);
  root.style.setProperty("--color-primary-fg", onBrand);
  root.style.setProperty("--color-hover", fillSoft);
  root.style.setProperty("--color-active", fill);
  root.style.setProperty("--color-info", hover);
  root.style.setProperty("--color-info-bg", fillSoft);
  root.style.setProperty("--color-info-border", border);
  root.style.setProperty("--focus-ring", `rgb(${rgb} / 0.28)`);
  root.style.setProperty("--selection-bg", `rgb(${rgb} / ${isDark ? 0.28 : 0.22})`);
  root.style.setProperty("--color-spinner-track", fillSoft);
  root.style.setProperty("--grid-line", isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)");
  root.style.setProperty("--overlay", isDark ? "rgb(0 0 0 / 0.72)" : "rgb(0 0 0 / 0.4)");
  root.style.setProperty("--studio-font", FONT_BASE);
  root.style.setProperty("--studio-sidebar-w", "16.5rem");

  // Semantic tones (iOS system red / green / orange).
  if (isDark) {
    root.style.setProperty("--color-danger", "#FF453A");
    root.style.setProperty("--color-danger-fg", "#FF6961");
    root.style.setProperty("--color-danger-bg", "rgb(255 69 58 / 0.16)");
    root.style.setProperty("--color-danger-border", "rgb(255 69 58 / 0.4)");
    root.style.setProperty("--color-success", "#32D74B");
    root.style.setProperty("--color-success-fg", "#30D158");
    root.style.setProperty("--color-success-bg", "rgb(50 215 75 / 0.14)");
    root.style.setProperty("--color-success-border", "rgb(50 215 75 / 0.38)");
    root.style.setProperty("--color-warning", "#FFD60A");
    root.style.setProperty("--color-warning-fg", "#FFD60A");
    root.style.setProperty("--color-warning-bg", "rgb(255 214 10 / 0.12)");
    root.style.setProperty("--color-warning-border", "rgb(255 214 10 / 0.35)");
    root.style.setProperty("--studio-danger", "#FF453A");
    root.style.setProperty("--studio-danger-bg", "rgb(255 69 58 / 0.16)");
    root.style.setProperty("--studio-success", "#32D74B");
  } else {
    root.style.setProperty("--color-danger", "#FF3B30");
    root.style.setProperty("--color-danger-fg", "#D70015");
    root.style.setProperty("--color-danger-bg", "rgb(255 59 48 / 0.1)");
    root.style.setProperty("--color-danger-border", "rgb(255 59 48 / 0.32)");
    root.style.setProperty("--color-success", "#34C759");
    root.style.setProperty("--color-success-fg", "#248A3D");
    root.style.setProperty("--color-success-bg", "rgb(52 199 89 / 0.12)");
    root.style.setProperty("--color-success-border", "rgb(52 199 89 / 0.32)");
    root.style.setProperty("--color-warning", "#FF9F0A");
    root.style.setProperty("--color-warning-fg", "#C93400");
    root.style.setProperty("--color-warning-bg", "rgb(255 159 10 / 0.12)");
    root.style.setProperty("--color-warning-border", "rgb(255 159 10 / 0.3)");
    root.style.setProperty("--studio-danger", "#FF3B30");
    root.style.setProperty("--studio-danger-bg", "rgb(255 59 48 / 0.1)");
    root.style.setProperty("--studio-success", "#34C759");
  }
}

/** @deprecated kept for leftover imports; always Black. */
export type BrandId = "black";
export const BRAND_IDS: BrandId[] = ["black"];
export const BRAND_OPTIONS: { id: BrandId; label: string; swatch: string; blurb: string }[] = [
  { id: "black", label: "Black", swatch: ACCENT_DARK, blurb: "Ambient glass · system blue" },
];
export const BRANDS = {
  black: {
    id: "black" as const,
    darkRgb: RGB_DARK,
    lightRgb: RGB_LIGHT,
    dark: ACCENT_DARK,
    darkHover: ACCENT_DARK_HOVER,
    light: ACCENT_LIGHT,
    lightHover: ACCENT_LIGHT_HOVER,
    darkOnBrand: "#ffffff",
    lightOnBrand: "#ffffff",
    darkSurface,
    lightSurface,
  },
};
