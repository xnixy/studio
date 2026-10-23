import { Spinner } from "../../components/Spinner";
import type { AdminJobRow, AdminJobStats } from "../../types";
import type { WithBusy } from "./types";
import { Select } from "../../components/Select";
import { Button } from "../../ui";
import { adminTable as t } from "./tableClasses";

export function JobsTab({
  jobStatus,
  onStatus,
  jobStats,
  jobs,
  loading,
  busy,
  withBusy,
  onCancel,
}: {
  jobStatus: string;
  onStatus: (value: string) => void;
  jobStats: AdminJobStats | undefined;
  jobs: AdminJobRow[] | undefined;
  loading: boolean;
  busy: boolean;
  withBusy: WithBusy;
  onCancel: (jobId: string) => Promise<void>;
}) {
  return (
    <div className={t.stack}>
      <p className={t.lead}>Background work (renders, email, cleanup). Cancel stuck jobs.</p>
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        <Select
          value={jobStatus}
          fullWidth={false}
          onChange={(event) => onStatus(event.target.value)}
          aria-label="Filter jobs by status"
        >
          <option value="">All statuses</option>
          <option value="queued">queued</option>
          <option value="running">running</option>
          <option value="failed">failed</option>
          <option value="completed">completed</option>
          <option value="canceled">canceled</option>
        </Select>
      </div>
      <p className={t.subtle}>
        Stats, queued {jobStats?.queued ?? 0}, running {jobStats?.running ?? 0}, failed {jobStats?.failed ?? 0},
        completed {jobStats?.completed ?? 0}, canceled {jobStats?.canceled ?? 0}
      </p>
      {loading ? <Spinner /> : null}
      <div className={t.wrap}>
        <table className={t.table}>
          <thead>
            <tr>
              <th className={t.th}>Type</th>
              <th className={t.th}>Status</th>
              <th className={t.th}>Attempts</th>
              <th className={t.th}>Workspace</th>
              <th className={t.th}>Error</th>
              <th className={t.th}>Created</th>
              <th className={t.th} />
            </tr>
          </thead>
          <tbody>
            {(jobs || []).map((job) => (
              <tr key={job.id} className="hover:bg-[var(--studio-fill-quiet)]">
                <td className={t.td}>{job.job_type}</td>
                <td className={t.td}>{job.status}</td>
                <td className={t.td}>{job.attempts}</td>
                <td className={t.td}>
                  <code className={t.code}>{job.workspace_id.slice(0, 8)}</code>
                </td>
                <td className={t.tdMuted}>{job.error_message || "—"}</td>
                <td className={t.td}>{new Date(job.created_at).toLocaleString()}</td>
                <td className={t.td}>
                  {job.status === "queued" || job.status === "running" || job.status === "waiting_for_provider" ? (
                    <Button
                      variant="secondary"
                      size="small"
                      type="button"
                      disabled={busy}
                      onClick={() => void withBusy(() => onCancel(job.id), "Job cancel requested")}
                    >
                      Cancel
                    </Button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!jobs?.length && !loading ? <div className={t.empty}>No jobs.</div> : null}
    </div>
  );
}
