import { useQuery } from "@tanstack/react-query";
import { ScrollText, Settings as SettingsIcon, ShieldCheck } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { getAuditLog } from "@/services/audit";

const ACTION_LABELS: Record<string, string> = {
  "auth.register": "Account created",
  "auth.login_success": "Signed in",
  "auth.login_failed": "Failed sign-in attempt",
  "auth.login_blocked_inactive": "Sign-in blocked (inactive account)",
  "application.status_changed": "Application status changed",
  "automation.state_changed": "Automation state changed",
  "automation.rules_updated": "Automation rules updated",
  "resume.deleted": "Resume deleted",
};

function actionLabel(action: string): string {
  return ACTION_LABELS[action] ?? action;
}

export default function Settings() {
  const { user } = useAuth();
  const { data: auditLog, isLoading } = useQuery({
    queryKey: ["audit-log"],
    queryFn: () => getAuditLog(100),
  });

  return (
    <div className="space-y-6 p-8">
      <div>
        <h1 className="flex items-center gap-2 text-xl font-semibold">
          <SettingsIcon size={20} className="text-brand-600" /> Settings
        </h1>
        <p className="text-sm text-slate-500">Account details and your security audit log.</p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Account</h2>
        <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-xs text-slate-400">Email</dt>
            <dd className="font-medium">{user?.email}</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-400">Name</dt>
            <dd className="font-medium">
              {[user?.first_name, user?.last_name].filter(Boolean).join(" ") || "—"}
            </dd>
          </div>
        </dl>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="mb-1 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
          <ShieldCheck size={15} /> Security audit log
        </h2>
        <p className="mb-4 text-xs text-slate-400">
          Every sign-in, application status change, automation change, and resume deletion on your
          account, newest first.
        </p>

        {isLoading && <p className="text-sm text-slate-500">Loading audit log...</p>}
        {!isLoading && auditLog?.length === 0 && (
          <p className="text-sm text-slate-400">No activity recorded yet.</p>
        )}

        <div className="space-y-1.5">
          {auditLog?.map((entry) => (
            <div
              key={entry.id}
              className="flex items-start justify-between gap-3 rounded-lg border border-slate-100 px-3 py-2 text-sm dark:border-slate-800"
            >
              <div className="flex items-start gap-2">
                <ScrollText size={14} className="mt-0.5 shrink-0 text-slate-400" />
                <div>
                  <div className="font-medium">{actionLabel(entry.action)}</div>
                  {entry.detail && <div className="text-xs text-slate-500">{entry.detail}</div>}
                </div>
              </div>
              <div className="shrink-0 text-right text-xs text-slate-400">
                <div>{new Date(entry.created_at).toLocaleString()}</div>
                {entry.ip_address && <div>{entry.ip_address}</div>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
