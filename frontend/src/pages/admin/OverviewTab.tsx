import type { ReactNode } from "react";
import type { AdminJobStats, AdminOverview } from "../../types";
import { adminTable as t } from "./tableClasses";

export function OverviewTab({
  overview,
  jobStats,
  contactCount,
}: {
  overview: AdminOverview | undefined;
  jobStats: AdminJobStats | undefined;
  contactCount: number;
}) {
  const ov = overview;
  const rows: [string, ReactNode][] = [
    ["Disabled accounts", ov?.disabled_users ?? 0],
    ["Inbox (open)", `${ov?.contacts_open ?? 0} / ${ov?.contacts_total ?? contactCount}`],
    ["Clip renders queued / running", `${ov?.renders_queued ?? 0} / ${ov?.renders_running ?? 0}`],
    ["Redis", ov?.redis_healthy ? "Healthy" : "Fallback / down"],
    ["FFmpeg", ov?.ffmpeg_available ? "Available" : "Missing"],
    ["Media storage", ov?.r2_enabled ? "R2" : "Local"],
    ["xAI (image / video / TTS)", ov?.xai_configured ? "Configured" : "Not configured"],
    ["Stripe credits", ov?.stripe_configured ? "Configured" : "Safe mode"],
    [
      "Plans in use",
      ov?.subscriptions_by_plan
        ? Object.entries(ov.subscriptions_by_plan)
            .map(([plan, count]) => `${plan}: ${count}`)
            .join(" · ") || "—"
        : "—",
    ],
    [
      "Background jobs",
      `queued ${jobStats?.queued ?? ov?.jobs_queued ?? 0} · running ${jobStats?.running ?? ov?.jobs_running ?? 0} · failed ${jobStats?.failed ?? ov?.jobs_failed ?? 0}`,
    ],
  ];

  return (
    <div className={t.stack}>
      <p className={t.lead}>
        Ops for avatar-first studio: people, spaces, credits, and clip generation health. Secrets never show here.
      </p>
      <div className={t.wrap}>
        <table className={`${t.table} min-w-0`}>
          <tbody>
            {rows.map(([label, value]) => (
              <tr key={label} className="hover:bg-[var(--studio-fill-quiet)]">
                <td className={`${t.td} w-[40%] font-semibold text-[var(--studio-fg-muted)]`}>{label}</td>
                <td className={t.td}>{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
