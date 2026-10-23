import type { ReactNode } from "react";
import { cn } from "../lib/cn";
import { tw } from "./tw";

export type StatusTone = "neutral" | "brand" | "success" | "warning" | "danger" | "muted";

const TONE_CLASS: Record<StatusTone, string> = {
  neutral: tw.badgeSubtle,
  brand: tw.badgeBrand,
  success: tw.badgeSuccess,
  warning: tw.badgeWarning,
  danger: tw.badgeDanger,
  muted: tw.badgeSubtle,
};

/** Human labels + tones for common workspace statuses. */
export function statusPresentation(raw: string): { label: string; tone: StatusTone } {
  const key = (raw || "").toLowerCase().replace(/\s+/g, "_");
  const map: Record<string, { label: string; tone: StatusTone }> = {
    open: { label: "Open", tone: "brand" },
    accepted: { label: "Accepted", tone: "success" },
    dismissed: { label: "Dismissed", tone: "muted" },
    converted: { label: "In a test", tone: "brand" },
    candidate: { label: "Worth testing", tone: "brand" },
    proven: { label: "Proven", tone: "success" },
    retired: { label: "Retired", tone: "muted" },
    rejected: { label: "Passed on", tone: "muted" },
    draft: { label: "Draft", tone: "neutral" },
    running: { label: "Running", tone: "brand" },
    completed: { label: "Done", tone: "success" },
    complete: { label: "Done", tone: "success" },
    abandoned: { label: "Stopped", tone: "muted" },
    failed: { label: "Failed", tone: "danger" },
    queued: { label: "Queued", tone: "neutral" },
    processing: { label: "Working", tone: "brand" },
    committing: { label: "Saving", tone: "brand" },
    committed: { label: "Saved", tone: "success" },
    pending: { label: "Pending", tone: "neutral" },
    active: { label: "Active", tone: "success" },
    disabled: { label: "Off", tone: "muted" },
    enabled: { label: "On", tone: "success" },
    approved: { label: "Approved", tone: "success" },
    changes_requested: { label: "Changes", tone: "warning" },
    connected: { label: "Connected", tone: "success" },
    disconnected: { label: "Disconnected", tone: "muted" },
    error: { label: "Error", tone: "danger" },
    low: { label: "Low risk", tone: "success" },
    medium: { label: "Medium risk", tone: "warning" },
    high: { label: "High risk", tone: "danger" },
    critical: { label: "Critical", tone: "danger" },
  };
  return map[key] || { label: raw || "Unknown", tone: "neutral" };
}

export function confidenceLabel(score: number | null | undefined): string {
  if (score == null || Number.isNaN(score)) return "";
  if (score >= 75) return "Strong signal";
  if (score >= 50) return "Medium signal";
  return "Light signal";
}

export function StatusChip({
  status,
  label,
  tone,
  title,
  children,
}: {
  status?: string;
  label?: string;
  tone?: StatusTone;
  title?: string;
  children?: ReactNode;
}) {
  const pres = status != null ? statusPresentation(status) : null;
  const text = children ?? label ?? pres?.label ?? status ?? "";
  const toneCls = TONE_CLASS[tone ?? pres?.tone ?? "neutral"];
  return (
    <span className={cn(tw.badge, toneCls)} title={title}>
      {text}
    </span>
  );
}
