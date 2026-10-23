import { isHtmlBootActive } from "../bootShell";
import { tw } from "./tw";

export function Spinner({ label = "Loading" }: { label?: string }) {
  if (isHtmlBootActive()) {
    return null;
  }

  return (
    <div className="grid min-h-32 place-items-center gap-2.5 p-6 text-sm text-[var(--studio-fg-muted)]">
      <div className={tw.spinner} aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
