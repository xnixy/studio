import { useCallback, useMemo, useState } from "react";
import { Spinner } from "../../components/Spinner";
import type { AdminAuditPage, AdminAuditRow } from "../../types";
import { Button, Input, Select } from "../../ui";
import { adminTable as t } from "./tableClasses";

const ACTION_PRESETS = [
  "",
  "admin.",
  "billing.",
  "play.",
  "job.",
  "face.",
  "asset.",
  "iap.",
] as const;

function formatWhen(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso;
  }
}

function summarizeDetails(details: Record<string, unknown> | null | undefined): string {
  if (!details || typeof details !== "object") return "—";
  const entries = Object.entries(details);
  if (!entries.length) return "—";

  const parts: string[] = [];
  for (const [key, value] of entries.slice(0, 6)) {
    if (value == null || value === "") continue;
    if (typeof value === "object") {
      try {
        const s = JSON.stringify(value);
        parts.push(`${key}: ${s.length > 80 ? `${s.slice(0, 80)}…` : s}`);
      } catch {
        parts.push(`${key}: [object]`);
      }
    } else {
      const s = String(value);
      parts.push(`${key}: ${s.length > 60 ? `${s.slice(0, 60)}…` : s}`);
    }
  }
  if (entries.length > 6) parts.push(`+${entries.length - 6} more`);
  return parts.length ? parts.join(" · ") : "—";
}

function detailsJson(details: Record<string, unknown> | null | undefined): string {
  if (!details) return "{}";
  try {
    return JSON.stringify(details, null, 2);
  } catch {
    return String(details);
  }
}

function actorLabel(row: AdminAuditRow): string {
  if (row.actor_name?.trim()) {
    return row.actor_email ? `${row.actor_name} (${row.actor_email})` : row.actor_name;
  }
  if (row.actor_email) return row.actor_email;
  if (row.actor_id) return row.actor_id.slice(0, 8);
  return "System";
}

function accountLabel(row: AdminAuditRow): string {
  const name = row.workspace_name?.trim() || null;
  const owner = row.owner_email?.trim() || null;
  if (name && owner) return `${name} · ${owner}`;
  if (owner) return owner;
  if (name) return name;
  return row.workspace_id.slice(0, 8);
}

function csvEscape(value: string): string {
  if (/[",\n\r]/.test(value)) return `"${value.replace(/"/g, '""')}"`;
  return value;
}

function rowsToCsv(rows: AdminAuditRow[]): string {
  const header = [
    "created_at",
    "action",
    "actor_email",
    "actor_name",
    "actor_id",
    "workspace_id",
    "workspace_name",
    "owner_email",
    "details",
  ];
  const lines = [header.join(",")];
  for (const row of rows) {
    lines.push(
      [
        row.created_at,
        row.action,
        row.actor_email || "",
        row.actor_name || "",
        row.actor_id || "",
        row.workspace_id,
        row.workspace_name || "",
        row.owner_email || "",
        JSON.stringify(row.details || {}),
      ]
        .map((cell) => csvEscape(String(cell)))
        .join(","),
    );
  }
  return `${lines.join("\n")}\n`;
}

function downloadText(filename: string, text: string, mime: string) {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function AuditTab({
  page,
  loading,
  error,
  actionFilter,
  onActionFilter,
  search,
  onSearch,
  since,
  onSince,
  until,
  onUntil,
  pageSize,
  onPageSize,
  onPrev,
  onNext,
  onRefresh,
  onExport,
  exporting,
  onOpenAccount,
}: {
  page: AdminAuditPage | undefined;
  loading: boolean;
  error?: string | null;
  actionFilter: string;
  onActionFilter: (value: string) => void;
  search: string;
  onSearch: (value: string) => void;
  since: string;
  onSince: (value: string) => void;
  until: string;
  onUntil: (value: string) => void;
  pageSize: number;
  onPageSize: (value: number) => void;
  onPrev: () => void;
  onNext: () => void;
  onRefresh: () => void;
  onExport: () => Promise<AdminAuditRow[]>;
  exporting?: boolean;
  onOpenAccount: (workspaceId: string) => void;
}) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const items = page?.items ?? [];
  const total = page?.total ?? 0;
  const offset = page?.offset ?? 0;
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + items.length, total);
  const canPrev = offset > 0;
  const canNext = offset + items.length < total;

  const rangeLabel = useMemo(() => {
    if (loading && !page) return "Loading…";
    if (total === 0) return "0 events";
    return `${from}–${to} of ${total}`;
  }, [from, to, total, loading, page]);

  const handleExport = useCallback(async () => {
    setExportError(null);
    try {
      const rows = await onExport();
      if (!rows.length) {
        setExportError("Nothing to export for these filters.");
        return;
      }
      const stamp = new Date().toISOString().slice(0, 10);
      downloadText(`studio-audit-${stamp}.csv`, rowsToCsv(rows), "text/csv;charset=utf-8");
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "Export failed");
    }
  }, [onExport]);

  return (
    <div className={t.stack}>
      <p className={t.lead}>
        Platform activity: billing, admin changes, clip generation, jobs. Search people, filter by date or action,
        export CSV, or open an account.
      </p>

      <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-end">
        <label className="grid min-w-0 flex-[1.2] gap-1 text-[0.78rem] font-semibold text-[var(--studio-fg-muted)]">
          Search
          <Input
            value={search}
            placeholder="Email, name, action, account…"
            onChange={(_, data) => onSearch(data.value)}
            aria-label="Search audit log"
          />
        </label>
        <label className="grid min-w-[9rem] gap-1 text-[0.78rem] font-semibold text-[var(--studio-fg-muted)]">
          Action
          <Input
            value={actionFilter}
            list="admin-audit-action-presets"
            placeholder="e.g. billing."
            onChange={(_, data) => onActionFilter(data.value)}
            aria-label="Filter by action"
            spellCheck={false}
          />
          <datalist id="admin-audit-action-presets">
            {ACTION_PRESETS.filter(Boolean).map((p) => (
              <option key={p} value={p} />
            ))}
          </datalist>
        </label>
        <label className="grid min-w-[8.5rem] gap-1 text-[0.78rem] font-semibold text-[var(--studio-fg-muted)]">
          From
          <Input
            type="date"
            value={since}
            onChange={(_, data) => onSince(data.value)}
            aria-label="From date"
          />
        </label>
        <label className="grid min-w-[8.5rem] gap-1 text-[0.78rem] font-semibold text-[var(--studio-fg-muted)]">
          To
          <Input
            type="date"
            value={until}
            onChange={(_, data) => onUntil(data.value)}
            aria-label="To date"
          />
        </label>
        <label className="grid min-w-[7rem] gap-1 text-[0.78rem] font-semibold text-[var(--studio-fg-muted)]">
          Page size
          <Select
            value={String(pageSize)}
            fullWidth={false}
            onChange={(event) => onPageSize(Number(event.target.value) || 50)}
            aria-label="Audit page size"
          >
            <option value="25">25</option>
            <option value="50">50</option>
            <option value="100">100</option>
          </Select>
        </label>
        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" size="small" variant="secondary" disabled={loading} onClick={onRefresh}>
            Refresh
          </Button>
          <Button
            type="button"
            size="small"
            variant="secondary"
            disabled={loading || exporting || total === 0}
            onClick={() => void handleExport()}
          >
            {exporting ? "Exporting…" : "Export CSV"}
          </Button>
        </div>
      </div>

      <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
        <p className={t.subtle}>{rangeLabel}</p>
        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" size="small" variant="secondary" disabled={!canPrev || loading} onClick={onPrev}>
            Previous
          </Button>
          <Button type="button" size="small" variant="secondary" disabled={!canNext || loading} onClick={onNext}>
            Next
          </Button>
        </div>
      </div>

      {error ? <p className="m-0 text-sm text-[var(--color-danger-fg,var(--color-danger))]">{error}</p> : null}
      {exportError ? (
        <p className="m-0 text-sm text-[var(--color-danger-fg,var(--color-danger))]">{exportError}</p>
      ) : null}
      {loading && !items.length ? <Spinner /> : null}

      <div className={t.wrap}>
        <table className={t.table}>
          <thead>
            <tr>
              <th className={t.th}>When</th>
              <th className={t.th}>Action</th>
              <th className={t.th}>Actor</th>
              <th className={t.th}>Account</th>
              <th className={t.th}>Details</th>
              <th className={t.th} />
            </tr>
          </thead>
          <tbody>
            {items.map((row) => {
              const open = expandedId === row.id;
              return (
                <tr key={row.id} className="align-top hover:bg-[var(--studio-fill-quiet)]">
                  <td className={t.td}>
                    <time dateTime={row.created_at} className="whitespace-nowrap text-[0.82rem]">
                      {formatWhen(row.created_at)}
                    </time>
                  </td>
                  <td className={t.td}>
                    <code className="rounded bg-[var(--studio-fill-soft)] px-1.5 py-0.5 font-mono text-[0.78rem]">
                      {row.action}
                    </code>
                  </td>
                  <td className={t.td}>
                    <div className="grid min-w-0 gap-0.5">
                      <span className="truncate text-[0.88rem] font-medium">{actorLabel(row)}</span>
                      {row.actor_id ? (
                        <span className={t.subtle}>
                          <code className={t.code}>{row.actor_id.slice(0, 8)}</code>
                        </span>
                      ) : null}
                    </div>
                  </td>
                  <td className={t.td}>
                    <div className="grid min-w-0 gap-0.5">
                      <button
                        type="button"
                        className="m-0 cursor-pointer truncate border-0 bg-transparent p-0 text-left text-[0.88rem] font-medium text-[var(--studio-brand)] hover:underline"
                        onClick={() => onOpenAccount(row.workspace_id)}
                        title="Open account controls"
                      >
                        {accountLabel(row)}
                      </button>
                      <span className={t.subtle}>
                        <code className={t.code}>{row.workspace_id.slice(0, 8)}</code>
                      </span>
                    </div>
                  </td>
                  <td className={t.tdMuted}>
                    <button
                      type="button"
                      className="m-0 max-w-[20rem] cursor-pointer border-0 bg-transparent p-0 text-left text-[0.82rem] leading-snug text-[var(--studio-fg-muted)] hover:text-[var(--studio-fg)]"
                      onClick={() => setExpandedId(open ? null : row.id)}
                      aria-expanded={open}
                    >
                      {open ? (
                        <pre className="m-0 max-h-48 overflow-auto whitespace-pre-wrap break-all rounded-lg border border-[var(--studio-border-soft)] bg-[var(--studio-fill-quiet)] p-2 font-mono text-[0.75rem] text-[var(--studio-fg)]">
                          {detailsJson(row.details)}
                        </pre>
                      ) : (
                        <span className="line-clamp-2">{summarizeDetails(row.details)}</span>
                      )}
                    </button>
                  </td>
                  <td className={t.td}>
                    <Button
                      type="button"
                      size="small"
                      variant="secondary"
                      onClick={() => onOpenAccount(row.workspace_id)}
                    >
                      Account
                    </Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {!loading && !items.length ? <div className={t.empty}>No audit events match.</div> : null}

      {items.length > 0 ? (
        <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
          <p className={t.subtle}>{rangeLabel}</p>
          <div className="flex flex-wrap items-center gap-2">
            <Button type="button" size="small" variant="secondary" disabled={!canPrev || loading} onClick={onPrev}>
              Previous
            </Button>
            <Button type="button" size="small" variant="secondary" disabled={!canNext || loading} onClick={onNext}>
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
