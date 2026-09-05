import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { listApplications } from "@/services/applications";
import { APPLICATION_STATUSES } from "@/types/application";

const STATUS_COLORS: Record<string, string> = {
  discovered: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  matched: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  saved: "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  preparing: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  ready_for_review: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  needs_manual_review: "bg-orange-50 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
  submitted: "bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-200",
  assessment: "bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
  interview: "bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
  offer: "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  rejected: "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300",
  withdrawn: "bg-slate-100 text-slate-400 dark:bg-slate-800",
};

export default function Applications() {
  const [statusFilter, setStatusFilter] = useState("");
  const { data: applications, isLoading } = useQuery({
    queryKey: ["applications", statusFilter],
    queryFn: () => listApplications(statusFilter || undefined),
  });

  return (
    <div className="space-y-6 p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Applications</h1>
          <p className="text-sm text-slate-500">Every job you've tracked, from discovery to offer.</p>
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
        >
          <option value="">All statuses</option>
          {APPLICATION_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      </div>

      {isLoading && <p className="text-sm text-slate-500">Loading applications...</p>}

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-100 text-xs uppercase tracking-wide text-slate-400 dark:border-slate-800">
            <tr>
              <th className="px-4 py-3">Job</th>
              <th className="px-4 py-3">Company</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Match</th>
              <th className="px-4 py-3">Discovered</th>
            </tr>
          </thead>
          <tbody>
            {applications?.map((app) => (
              <tr key={app.id} className="border-b border-slate-50 last:border-0 dark:border-slate-800/60">
                <td className="px-4 py-3">
                  <Link to={`/applications/${app.id}`} className="font-medium hover:text-brand-600">
                    {app.job.title}
                  </Link>
                </td>
                <td className="px-4 py-3 text-slate-500">{app.job.company.name}</td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${
                      STATUS_COLORS[app.status] ?? "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {app.status.replace(/_/g, " ")}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-500">
                  {app.match_score !== null ? `${app.match_score}%` : "—"}
                </td>
                <td className="px-4 py-3 text-slate-500">
                  {new Date(app.discovered_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {applications?.length === 0 && (
          <div className="p-8 text-center text-sm text-slate-400">
            No applications tracked yet. Save a job from its detail page to start tracking it here.
          </div>
        )}
      </div>
    </div>
  );
}
