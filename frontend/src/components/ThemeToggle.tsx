import { Check, Monitor, Moon, Sun } from "lucide-react";
import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { cn } from "../lib/cn";
import { tw } from "../ui/tw";
import { useStudioTheme, type ThemePreference } from "../ui/theme/themeContext";

type MenuCoords = { top: number; left: number };

export function ThemeToggle() {
  const { preference, setPreference } = useStudioTheme();
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState<MenuCoords | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  const themeItems: { value: ThemePreference; label: string; icon: ReactNode }[] = [
    { value: "system", label: "System", icon: <Monitor size={16} /> },
    { value: "dark", label: "Dark", icon: <Moon size={16} /> },
    { value: "light", label: "Light", icon: <Sun size={16} /> },
  ];

  const triggerIcon =
    preference === "light" ? <Sun size={18} /> : preference === "system" ? <Monitor size={18} /> : <Moon size={18} />;

  useLayoutEffect(() => {
    if (!open) {
      setCoords(null);
      return;
    }
    const place = () => {
      const trigger = rootRef.current;
      const menu = menuRef.current;
      if (!trigger) return;
      const rect = trigger.getBoundingClientRect();
      const menuWidth = menu?.offsetWidth || 180;
      const menuHeight = menu?.offsetHeight || 140;
      const gap = 6;
      const pad = 8;
      let top = rect.bottom + gap;
      if (top + menuHeight > window.innerHeight - pad) {
        top = Math.max(pad, rect.top - gap - menuHeight);
      }
      let left = rect.right - menuWidth;
      if (left < pad) left = pad;
      if (left + menuWidth > window.innerWidth - pad) {
        left = Math.max(pad, window.innerWidth - pad - menuWidth);
      }
      setCoords({ top, left });
    };
    place();
    const raf = requestAnimationFrame(place);
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent | TouchEvent) => {
      const target = e.target as Node;
      if (rootRef.current?.contains(target) || menuRef.current?.contains(target)) return;
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const menu =
    open && typeof document !== "undefined"
      ? createPortal(
          <div
            ref={menuRef}
            id={menuId}
            role="menu"
            className={cn(
              tw.menu,
              "fixed z-[120] max-h-[min(70vh,24rem)] w-[min(12rem,calc(100vw-1rem))] overflow-y-auto",
            )}
            style={{
              top: coords?.top ?? -9999,
              left: coords?.left ?? -9999,
              visibility: coords ? "visible" : "hidden",
            }}
          >
            {themeItems.map((item) => (
              <button
                key={item.value}
                type="button"
                role="menuitem"
                className={cn(tw.menuItem, "min-h-10")}
                onClick={() => {
                  setPreference(item.value);
                  setOpen(false);
                }}
              >
                <span className="inline-grid shrink-0 place-items-center opacity-90">{item.icon}</span>
                <span>{item.label}</span>
                {preference === item.value ? (
                  <Check size={14} className="ml-auto shrink-0 text-[var(--studio-brand)]" />
                ) : null}
              </button>
            ))}
          </div>,
          document.body,
        )
      : null;

  return (
    <div className="relative inline-flex shrink-0" ref={rootRef}>
      <button
        type="button"
        className={cn(tw.btn, tw.btnMd, tw.btnSubtle, tw.btnIcon)}
        aria-label="Theme"
        title="Theme"
        aria-expanded={open}
        aria-haspopup="menu"
        aria-controls={menuId}
        onClick={() => setOpen((v) => !v)}
      >
        {triggerIcon}
      </button>
      {menu}
    </div>
  );
}
