import { cn } from "../lib/cn";

/**
 * Glass Antiqua "Studio" wordmark as inline SVG.
 * Fill uses currentColor → var(--studio-brand).
 */
export function BrandLogo({ size = "md", className }: { size?: "sm" | "md"; className?: string }) {
  return (
    <svg
      className={cn(
        "block w-auto shrink-0 overflow-visible text-[var(--studio-brand)]",
        size === "sm" ? "h-[22px] max-w-28" : "h-7 max-w-[140px]",
        className,
      )}
      viewBox="0 0 220 45"
      width={220}
      height={45}
      role="img"
      aria-label="Studio"
      xmlns="http://www.w3.org/2000/svg"
    >
      <text
        x="8"
        y="38"
        fill="currentColor"
        style={{
          fontFamily: '"Glass Antiqua", Georgia, "Times New Roman", serif',
          fontWeight: 400,
          fontSize: 65,
        }}
      >
        Studio
      </text>
    </svg>
  );
}
