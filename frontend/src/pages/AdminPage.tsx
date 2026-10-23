import { FormEvent, useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, api } from "../api";
import { useAuth } from "../auth";
import { Spinner } from "../components/Spinner";
import type { Role } from "../types";
import { AuditTab } from "./admin/AuditTab";
import { JobsTab } from "./admin/JobsTab";
import {
  ContactsTab,
  MaintenanceTab,
  UsageTab,
  AccountsTab,
} from "./admin/OpsTabs";
import { OverviewTab } from "./admin/OverviewTab";
import type { AdminTab } from "./admin/types";
import { UsersTab } from "./admin/UsersTab";
import { MessageBar, Page, PageBoard, PageHeader, PageSection, StatCard, Tabs } from "../ui";

export function AdminPage() {
  const auth = useAuth();
  const queryClient = useQueryClient();
  // Prefer accessToken + enabled over requireToken() at render (throws if signed out).
  const token = auth.accessToken ?? "";
  const authed = Boolean(auth.accessToken);
  const [maintenanceEnabled, setMaintenanceEnabled] = useState(false);
  const [maintenanceMessage, setMaintenanceMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState<AdminTab>("overview");
  const [userFilter, setUserFilter] = useState("");
  const [jobStatus, setJobStatus] = useState("");
  const [auditOffset, setAuditOffset] = useState(0);
  const [auditPageSize, setAuditPageSize] = useState(50);
  const [auditAction, setAuditAction] = useState("");
  const [auditSearch, setAuditSearch] = useState("");
  const [auditSearchDebounced, setAuditSearchDebounced] = useState("");
  const [auditSince, setAuditSince] = useState("");
  const [auditUntil, setAuditUntil] = useState("");
  const [auditExporting, setAuditExporting] = useState(false);
  const [focusAccountId, setFocusAccountId] = useState<string | null>(null);

  const overview = useQuery({
    queryKey: ["admin", "overview"],
    queryFn: () => api.adminOverview(token),
    enabled: authed && tab === "overview",
    staleTime: 30_000,
  });
  const users = useQuery({
    queryKey: ["admin", "users"],
    queryFn: () => api.listUsers(token),
    enabled: authed && (tab === "users" || tab === "overview"),
  });
  const contacts = useQuery({
    queryKey: ["admin", "contacts"],
    queryFn: () => api.listContacts(token),
    enabled: authed && (tab === "inbox" || tab === "overview"),
  });
  const maintenance = useQuery({
    queryKey: ["admin", "maintenance"],
    queryFn: () => api.adminMaintenance(token),
    enabled: authed && (tab === "maintenance" || tab === "overview"),
  });
  const workspaces = useQuery({
    queryKey: ["admin", "workspaces"],
    queryFn: () => api.adminWorkspaces(token),
    enabled: authed && (tab === "accounts" || tab === "overview"),
  });
  const jobStats = useQuery({
    queryKey: ["admin", "job-stats"],
    queryFn: () => api.adminJobStats(token),
    enabled: authed && (tab === "jobs" || tab === "overview"),
  });
  const jobs = useQuery({
    queryKey: ["admin", "jobs", jobStatus],
    queryFn: () => api.adminJobs(token, jobStatus || undefined),
    enabled: authed && tab === "jobs",
  });
  const usage = useQuery({
    queryKey: ["admin", "usage"],
    queryFn: () => api.adminUsage(token),
    enabled: authed && tab === "usage",
  });
  const auditFilters = useMemo(
    () => ({
      action: auditAction || undefined,
      q: auditSearchDebounced || undefined,
      since: auditSince || undefined,
      until: auditUntil || undefined,
    }),
    [auditAction, auditSearchDebounced, auditSince, auditUntil],
  );

  const audit = useQuery({
    queryKey: ["admin", "audit", auditOffset, auditPageSize, auditFilters],
    queryFn: () =>
      api.adminAudit(token, {
        limit: auditPageSize,
        offset: auditOffset,
        ...auditFilters,
      }),
    enabled: authed && tab === "audit",
    placeholderData: (prev) => prev,
  });

  const loading =
    (tab === "overview" && overview.isLoading) ||
    (tab === "users" && users.isLoading) ||
    (tab === "inbox" && contacts.isLoading) ||
    (tab === "maintenance" && maintenance.isLoading);

  useEffect(() => {
    const id = window.setTimeout(() => setAuditSearchDebounced(auditSearch.trim()), 300);
    return () => window.clearTimeout(id);
  }, [auditSearch]);

  useEffect(() => {
    setAuditOffset(0);
  }, [auditAction, auditSearchDebounced, auditPageSize, auditSince, auditUntil]);

  useEffect(() => {
    if (tab !== "accounts" || !focusAccountId) return;
    const id = window.setTimeout(() => {
      document.getElementById(`admin-account-${focusAccountId}`)?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }, 120);
    return () => window.clearTimeout(id);
  }, [tab, focusAccountId, workspaces.data]);

  useEffect(() => {
    if (maintenance.data) {
      setMaintenanceEnabled(maintenance.data.enabled);
      setMaintenanceMessage(maintenance.data.message || "");
    }
  }, [maintenance.data]);

  const filteredUsers = useMemo(() => {
    const rows = users.data || [];
    const q = userFilter.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((user) =>
      [user.email, user.full_name, user.role].filter(Boolean).join(" ").toLowerCase().includes(q),
    );
  }, [userFilter, users.data]);

  async function withBusy(action: () => Promise<void>, success?: string) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      if (success) setNotice(success);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Admin action failed");
    } finally {
      setBusy(false);
    }
  }

  async function invalidateAdmin(...keys: string[]) {
    for (const key of keys) {
      await queryClient.invalidateQueries({ queryKey: ["admin", key] });
    }
  }

  if (loading) return <Spinner />;

  const ov = overview.data;
  const userCount = users.data?.length || 0;
  const adminCount = users.data?.filter((user) => user.role === "admin").length || 0;
  const contactOpen = ov?.contacts_open ?? contacts.data?.filter((c) => !c.resolved_at).length ?? 0;

  const tabs: { value: AdminTab; label: string }[] = [
    { value: "overview", label: "Overview" },
    { value: "users", label: `People (${userCount})` },
    { value: "accounts", label: "Accounts" },
    { value: "usage", label: "Credits" },
    { value: "jobs", label: "Jobs" },
    { value: "inbox", label: `Inbox (${contactOpen})` },
    { value: "maintenance", label: "Maintenance" },
    { value: "audit", label: "Audit" },
  ];

  return (
    <Page wide>
      <PageHeader
        title="Ops"
        subtitle="People, accounts, credits, and clip generation."
      />

      {error ? <MessageBar intent="error">{error}</MessageBar> : null}
      {notice ? <MessageBar intent="success">{notice}</MessageBar> : null}

      <section className="mb-1 grid grid-cols-2 gap-3 md:grid-cols-4" aria-label="Ops summary">
        <StatCard
          icon="M"
          label="Maintenance"
          value={ov?.maintenance_enabled || maintenance.data?.enabled ? "On" : "Off"}
        />
        <StatCard
          icon="P"
          label={`People · ${ov?.admins ?? adminCount} admin`}
          value={ov?.users ?? userCount}
        />
        <StatCard icon="A" label="Accounts" value={ov?.workspaces ?? "—"} />
        <StatCard
          icon="C"
          label={`Clip jobs · ${ov?.jobs_failed ?? 0} failed`}
          value={(ov?.jobs_queued ?? 0) + (ov?.jobs_running ?? 0) + (ov?.renders_running ?? 0)}
        />
      </section>

      <PageBoard>
        <Tabs
          aria-label="Ops sections"
          value={tab}
          onChange={(v) => setTab(v as AdminTab)}
          size="small"
          items={tabs}
        />

        <PageSection>
          {tab === "overview" ? (
            <OverviewTab
              overview={overview.data}
              jobStats={jobStats.data}
              contactCount={contacts.data?.length || 0}
            />
          ) : null}

          {tab === "users" ? (
            <UsersTab
              users={filteredUsers}
              filter={userFilter}
              onFilter={setUserFilter}
              busy={busy}
              selfId={auth.user?.id}
              withBusy={withBusy}
              onRole={async (userId, role: Role) => {
                await api.updateAdminUser(userId, { role }, token);
                await invalidateAdmin("users", "overview");
              }}
              onToggleDisabled={async (userId, is_disabled) => {
                await api.updateAdminUser(userId, { is_disabled }, token);
                await invalidateAdmin("users", "overview");
              }}
              onRevoke={async (userId) => {
                await api.revokeUserSessions(userId, token);
              }}
            />
          ) : null}

          {tab === "accounts" ? (
            <AccountsTab
              rows={workspaces.data}
              loading={workspaces.isLoading}
              busy={busy}
              focusId={focusAccountId}
              onAccount={async (id, payload) => {
                await withBusy(async () => {
                  await api.updateAdminWorkspace(id, payload, token);
                  await invalidateAdmin("workspaces", "overview", "usage", "audit");
                }, "Account controls saved");
              }}
              onGrantBoost={async (workspaceId, payload) => {
                await withBusy(async () => {
                  await api.adminGrantBoost(
                    {
                      workspace_id: workspaceId,
                      addon_type: payload.addon_type,
                      quantity: payload.quantity,
                      notes: payload.notes,
                    },
                    token,
                  );
                  await invalidateAdmin("workspaces", "overview", "usage", "audit");
                }, "Monthly boost granted");
              }}
              onCancelBoost={async (workspaceId, addonType) => {
                await withBusy(async () => {
                  await api.adminCancelBoost(workspaceId, addonType, token);
                  await invalidateAdmin("workspaces", "overview", "usage", "audit");
                }, "Boost removed");
              }}
            />
          ) : null}

          {tab === "usage" ? <UsageTab rows={usage.data} loading={usage.isLoading} /> : null}

          {tab === "jobs" ? (
            <JobsTab
              jobStatus={jobStatus}
              onStatus={setJobStatus}
              jobStats={jobStats.data}
              jobs={jobs.data}
              loading={jobs.isLoading}
              busy={busy}
              withBusy={withBusy}
              onCancel={async (jobId) => {
                await api.adminCancelJob(jobId, token);
                await invalidateAdmin("jobs", "job-stats", "overview");
              }}
            />
          ) : null}

          {tab === "inbox" ? (
            <ContactsTab
              contacts={contacts.data}
              busy={busy}
              withBusy={withBusy}
              onResolve={async (id) => {
                await api.resolveContact(id, token);
                await invalidateAdmin("contacts", "overview");
              }}
            />
          ) : null}

          {tab === "maintenance" ? (
            <MaintenanceTab
              enabled={maintenanceEnabled}
              message={maintenanceMessage}
              onEnabled={setMaintenanceEnabled}
              onMessage={setMaintenanceMessage}
              busy={busy}
              onSubmit={(event: FormEvent) => {
                event.preventDefault();
                void withBusy(async () => {
                  const result = await api.setMaintenance(
                    maintenanceEnabled,
                    maintenanceMessage.trim() || null,
                    token,
                  );
                  setMaintenanceEnabled(result.enabled);
                  setMaintenanceMessage(result.message || "");
                  await queryClient.invalidateQueries({ queryKey: ["maintenance"] });
                  await invalidateAdmin("maintenance", "overview");
                }, "Maintenance settings saved");
              }}
            />
          ) : null}

          {tab === "audit" ? (
            <AuditTab
              page={audit.data}
              loading={audit.isFetching}
              error={
                audit.error
                  ? audit.error instanceof ApiError || audit.error instanceof Error
                    ? audit.error.message
                    : "Could not load audit log"
                  : null
              }
              actionFilter={auditAction}
              onActionFilter={setAuditAction}
              search={auditSearch}
              onSearch={setAuditSearch}
              since={auditSince}
              onSince={setAuditSince}
              until={auditUntil}
              onUntil={setAuditUntil}
              pageSize={auditPageSize}
              onPageSize={setAuditPageSize}
              onPrev={() => setAuditOffset((o) => Math.max(0, o - auditPageSize))}
              onNext={() => setAuditOffset((o) => o + auditPageSize)}
              onRefresh={() => void audit.refetch()}
              exporting={auditExporting}
              onExport={async () => {
                setAuditExporting(true);
                try {
                  const pageSize = 200;
                  const maxRows = 2000;
                  const all: Awaited<ReturnType<typeof api.adminAudit>>["items"] = [];
                  let offset = 0;
                  let total = Infinity;
                  while (offset < total && all.length < maxRows) {
                    const page = await api.adminAudit(token, {
                      limit: pageSize,
                      offset,
                      ...auditFilters,
                    });
                    all.push(...page.items);
                    total = page.total;
                    offset += page.items.length;
                    if (!page.items.length) break;
                  }
                  return all;
                } finally {
                  setAuditExporting(false);
                }
              }}
              onOpenAccount={(workspaceId) => {
                setFocusAccountId(workspaceId);
                setTab("accounts");
              }}
            />
          ) : null}
        </PageSection>
      </PageBoard>
    </Page>
  );
}
