import { FormEvent, useMemo } from "react";
import { Spinner } from "../../components/Spinner";
import type {
  AdminContact,
  AdminUsageRow,
  AdminWorkspaceRow,
} from "../../types";
import type { WithBusy } from "./types";
import { optionalTextFeedback } from "../../lib/formValidation";
import { Button, Checkbox, Field, Input, Select } from "../../ui";
import { adminTable as t } from "./tableClasses";

export function MaintenanceTab({
  enabled,
  message,
  onEnabled,
  onMessage,
  busy,
  onSubmit,
}: {
  enabled: boolean;
  message: string;
  onEnabled: (value: boolean) => void;
  onMessage: (value: string) => void;
  busy: boolean;
  onSubmit: (event: FormEvent) => void;
}) {
  const messageFb = useMemo(() => optionalTextFeedback(message, 500), [message]);

  return (
    <form className="grid gap-3" onSubmit={onSubmit} noValidate>
      <p className={t.lead}>When on, everyone except admins sees a maintenance screen.</p>
      <Checkbox label="Maintenance mode enabled" checked={enabled} onChange={(_, data) => onEnabled(Boolean(data.checked))} />
      <Field
        label="Public message"
        validationState={messageFb.state}
        validationMessage={messageFb.message}
      >
        <Input
          value={message}
          maxLength={500}
          placeholder="We will be back shortly."
          onChange={(_, data) => onMessage(data.value)}
          aria-invalid={messageFb.state === "error"}
        />
      </Field>
      <div className="flex flex-wrap items-center gap-2">
        <Button size="small" disabled={busy || messageFb.state === "error"} type="submit">
          Save maintenance
        </Button>
      </div>
    </form>
  );
}

const limitLabels: Record<string, string> = {
  video_credit_limit: "Video tokens / month",
  image_generation_limit: "Image tokens / month",
  avatar_lipsync_limit: "Clip credits / month",
  voiceover_seconds_limit: "TTS seconds",
  storage_gb_limit: "Storage (GB)",
  script_generation_limit: "Scripts",
  clone_slot_limit: "Clone slots",
};

const PLAN_OPTIONS = ["free", "starter", "creator", "studio"] as const;

const BOOST_OPTIONS: { value: string; label: string; hint: string }[] = [
  { value: "video_credits", label: "Scene + talking", hint: "+5 video tokens per unit / mo" },
  { value: "image_generations", label: "Stills", hint: "+3 still tokens per unit / mo" },
  { value: "avatar_lipsyncs", label: "Clip (legacy addon)", hint: "+5 clip credits per unit / mo" },
  { value: "script_generations", label: "Scripts", hint: "+1 script per unit / mo" },
  { value: "voiceover_minutes", label: "Voice minutes", hint: "+1 min TTS per unit / mo" },
  { value: "storage_gb", label: "Storage", hint: "+1 GB per unit" },
  { value: "priority_rendering", label: "Priority rendering", hint: "Turn on priority queue" },
];

const BOOST_LABELS: Record<string, string> = Object.fromEntries(
  BOOST_OPTIONS.map((o) => [o.value, o.label]),
);

/** Plan + meter overrides per personal account (no team members). */
export function AccountsTab({
  rows,
  loading,
  busy,
  onAccount,
  onGrantBoost,
  onCancelBoost,
  focusId,
}: {
  rows: AdminWorkspaceRow[] | undefined;
  loading: boolean;
  busy: boolean;
  onAccount: (
    id: string,
    payload: { plan?: string; subscription_status?: string; limit_overrides?: Record<string, number> },
  ) => Promise<void>;
  onGrantBoost: (
    workspaceId: string,
    payload: { addon_type: string; quantity: number; notes?: string | null },
  ) => Promise<void>;
  onCancelBoost: (workspaceId: string, addonType: string) => Promise<void>;
  /** Open and scroll to this workspace when set (e.g. from audit deep-link). */
  focusId?: string | null;
}) {
  return (
    <div className={t.stack}>
      <p className={t.lead}>
        Each person has one account for clips and credits. Adjust plan, monthly caps, or grant recurring boosts.
      </p>
      {loading ? <Spinner /> : null}
      {(rows || []).map((row) => (
        <details
          key={focusId === row.id ? `${row.id}-focus` : row.id}
          id={`admin-account-${row.id}`}
          ref={(node) => {
            if (node && focusId === row.id) node.open = true;
          }}
          className={`mb-4 overflow-hidden rounded-xl border bg-[var(--studio-glass,var(--studio-panel))] backdrop-blur-[var(--studio-material-blur,28px)] backdrop-saturate-150 ${
            focusId === row.id
              ? "border-[var(--studio-brand)] shadow-[0_0_0_1px_var(--studio-brand)]"
              : "border-[var(--studio-border)]"
          }`}
        >
          <summary className="cursor-pointer px-4 py-3"><strong>{row.owner_email || row.name}</strong> · {row.plan}
            <span className={t.subtle}><code>{row.id.slice(0, 8)}</code></span>
            {(row.boosts?.length || 0) > 0 ? (
              <span className={t.subtle}> · {row.boosts!.length} boost{(row.boosts!.length === 1 ? "" : "s")}</span>
            ) : null}
          </summary>
          <div className="grid gap-5 border-t border-[var(--studio-border-soft)] p-4">
            <form onSubmit={(event) => {
              event.preventDefault();
              const data = new FormData(event.currentTarget);
              const limit_overrides: Record<string, number> = {};
              Object.keys(limitLabels).forEach((key) => {
                const value = String(data.get(key) ?? "").trim();
                if (value) limit_overrides[key] = Number(value);
              });
              const cloneSlots = String(data.get("clone_slot_limit") ?? "").trim();
              if (cloneSlots) limit_overrides.clone_slot_limit = Number(cloneSlots);
              void onAccount(row.id, { plan: String(data.get("plan")), subscription_status: String(data.get("status")), limit_overrides });
            }}>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Plan">
                  <Select name="plan" defaultValue={row.plan}>
                    {PLAN_OPTIONS.map((v) => <option key={v} value={v}>{v}</option>)}
                  </Select>
                </Field>
                <Field label="Status">
                  <Select name="status" defaultValue={row.subscription_status}>
                    {["active", "trialing", "paused", "past_due", "canceled"].map((v) => <option key={v}>{v}</option>)}
                  </Select>
                </Field>
                {Object.entries(row.effective_limits || {}).map(([key, value]) => (
                  <Field label={limitLabels[key] || key} key={key}>
                    <Input name={key} type="number" min={0} step={1} defaultValue={String(row.limit_overrides?.[key] ?? value)} />
                  </Field>
                ))}
                <Field label="Clone slots">
                  <Input
                    name="clone_slot_limit"
                    type="number"
                    min={1}
                    step={1}
                    defaultValue={String(row.limit_overrides?.clone_slot_limit ?? 1)}
                  />
                </Field>
              </div>
              <p className={t.lead}>Saving sets absolute monthly caps (also applied to Create meters). For additive top-ups, use boosts below.</p>
              <Button size="small" type="submit" disabled={busy}>Save plan & caps</Button>
            </form>

            <div className="grid gap-3 border-t border-[var(--studio-border-soft)] pt-4">
              <p className="m-0 text-sm font-semibold text-[var(--studio-fg)]">Monthly boosts</p>
              <p className={t.lead}>
                Recurring additive units. Show under Billing → Monthly boosts and raise Usage this period caps.
              </p>
              {(row.boosts || []).length ? (
                <ul className="m-0 grid list-none gap-2 p-0">
                  {(row.boosts || []).map((boost) => (
                    <li
                      key={boost.id}
                      className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[var(--studio-border)] px-3 py-2"
                    >
                      <div className="grid min-w-0 gap-0.5">
                        <strong className="text-sm text-[var(--studio-fg)]">
                          {BOOST_LABELS[boost.addon_type] || boost.addon_type}
                        </strong>
                        <span className={t.subtle}>
                          qty {boost.quantity}
                          {boost.notes ? ` · ${boost.notes}` : ""}
                        </span>
                      </div>
                      <Button
                        variant="secondary"
                        size="small"
                        type="button"
                        disabled={busy}
                        onClick={() => void onCancelBoost(row.id, boost.addon_type)}
                      >
                        Remove
                      </Button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className={t.empty}>No active boosts.</p>
              )}
              <form
                className="grid gap-3 sm:grid-cols-[minmax(0,1.2fr)_6rem_minmax(0,1fr)_auto] sm:items-end"
                onSubmit={(event) => {
                  event.preventDefault();
                  const data = new FormData(event.currentTarget);
                  const addon_type = String(data.get("addon_type") || "").trim();
                  const quantity = Math.max(1, Number(data.get("quantity") || 1));
                  const notes = String(data.get("notes") || "").trim() || null;
                  if (!addon_type) return;
                  void onGrantBoost(row.id, { addon_type, quantity, notes }).then(() => {
                    event.currentTarget.reset();
                  });
                }}
              >
                <Field label="Boost type">
                  <Select name="addon_type" defaultValue="video_credits">
                    {BOOST_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Qty">
                  <Input name="quantity" type="number" min={1} max={500} step={1} defaultValue={1} />
                </Field>
                <Field label="Notes (optional)">
                  <Input name="notes" maxLength={500} placeholder="Support goodwill" />
                </Field>
                <Button size="small" type="submit" disabled={busy}>
                  Grant boost
                </Button>
              </form>
              <p className={t.subtle}>
                {BOOST_OPTIONS.map((o) => `${o.label}: ${o.hint}`).join(" · ")}
              </p>
            </div>
          </div>
        </details>
      ))}
      {!rows?.length && !loading ? <div className={t.empty}>No accounts yet.</div> : null}
    </div>
  );
}

export function UsageTab({ rows, loading }: { rows: AdminUsageRow[] | undefined; loading: boolean }) {
  return (
    <div className={t.stack}>
      <p className={t.lead}>Credit burn across accounts: clips, stills, photo, TTS.</p>
      {loading ? <Spinner /> : null}
      <div className={t.wrap}>
        <table className={t.table}>
        <thead>
          <tr>
            <th className={t.th}>Account</th>
            <th className={t.th}>Meter</th>
            <th className={t.th}>Used</th>
          </tr>
        </thead>
        <tbody>
          {(rows || []).map((row, index) => (
            <tr key={`${row.workspace_id}-${row.event_type}-${index}`}>
              <td className={t.td}>{row.workspace_name}</td>
              <td className={t.td}>{row.event_type}</td>
              <td className={t.td}>{row.total_quantity}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
      {!rows?.length && !loading ? <div className={t.empty}>No usage yet.</div> : null}
    </div>
  );
}

export function ContactsTab({
  contacts,
  busy,
  withBusy,
  onResolve,
}: {
  contacts: AdminContact[] | undefined;
  busy: boolean;
  withBusy: WithBusy;
  onResolve: (id: string) => Promise<void>;
}) {
  return (
    <div className={t.stack}>
      <p className={t.lead}>Messages from the contact form. Mark resolved when you’re done.</p>
      <div className={t.wrap}>
        <table className={t.table}>
        <thead>
          <tr>
            <th className={t.th}>From</th>
            <th className={t.th}>Topic</th>
            <th className={t.th}>Message</th>
            <th className={t.th}>Received</th>
            <th className={t.th}>Status</th>
            <th className={t.th} />
          </tr>
        </thead>
        <tbody>
          {(contacts || []).map((contact) => (
            <tr key={contact.id}>
              <td className={t.td}>
                <strong>{contact.name}</strong>
                <div className={t.subtle}>{contact.email}</div>
              </td>
              <td className={t.td}>{contact.topic}</td>
              <td className={t.tdMuted}>{contact.message}</td>
              <td className={t.td}>{new Date(contact.created_at).toLocaleString()}</td>
              <td className={t.td}>{contact.resolved_at ? "Resolved" : "Open"}</td>
              <td className={t.td}>
                {!contact.resolved_at ? (
                  <Button variant="secondary" size="small" type="button" disabled={busy} onClick={() => void withBusy(() => onResolve(contact.id), "Contact resolved")}>
                    Resolve
                  </Button>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
      {!contacts?.length ? <div className={t.empty}>No contact submissions yet.</div> : null}
    </div>
  );
}

