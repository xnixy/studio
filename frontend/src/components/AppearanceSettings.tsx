import { PageLabel, PageMuted, useStudioTheme, type ThemePreference } from "../ui";
import { cn } from "../lib/cn";

const MODE_OPTIONS: { id: ThemePreference; label: string; blurb: string }[] = [
  { id: "dark", label: "Dark", blurb: "Default studio look" },
  { id: "light", label: "Light", blurb: "Bright surfaces" },
  { id: "system", label: "System", blurb: "Match device" },
];

const chipBase =
  "inline-flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2.5 text-left font-inherit text-[var(--studio-fg)]";
const chipIdle = "border-[var(--studio-border)] bg-[var(--studio-fill-quiet)]";
const chipActive = "border-[var(--studio-brand)] bg-[var(--studio-fill)] text-[var(--studio-brand)]";

/** Light / dark / system only (this device). */
export function AppearanceSettings({
  showMode = true,
  compact = false,
}: {
  showMode?: boolean;
  compact?: boolean;
}) {
  const { preference, setPreference } = useStudioTheme();
  if (!showMode) return null;

  return (
    <div className="grid gap-2.5">
      <div>
        <PageLabel>Theme mode</PageLabel>
        {!compact ? <PageMuted>Dark, light, or follow system preference.</PageMuted> : null}
      </div>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Theme mode">
        {MODE_OPTIONS.map((opt) => {
          const active = preference === opt.id;
          return (
            <button
              key={opt.id}
              type="button"
              className={cn(chipBase, active ? chipActive : chipIdle)}
              onClick={() => setPreference(opt.id)}
              aria-pressed={active}
            >
              <span>
                <strong>{opt.label}</strong>
                {!compact ? (
                  <span className="mt-0.5 block text-[0.72rem] text-[var(--studio-fg-muted)]">{opt.blurb}</span>
                ) : null}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
