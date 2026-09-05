import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Gauge, Play, Zap } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import {
  getRapidApplySettings,
  getRapidApplyStats,
  listRapidApplyQueue,
  runRapidApplyCycle,
  updateRapidApplySettings,
} from "@/services/rapidApply";

const PRIORITY_LABELS: Record<number, string> = { 0: "P0", 1: "P1", 2: "P2", 3: "P3" };
const PRIORITY_COLORS: Record<number, string> = {
  0: "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  1: "bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-200",
  2: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  3: "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400",
};
const STATUS_COLORS: Record<string, string> = {
  queued: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  processing: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  completed: "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  skipped: "bg-slate-100 text-slate-400 dark:bg-slate-800",
  failed: "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300",
};

function formatSeconds(value: number | null): string {
  if (value === null) return "—";
  if (value < 1) return `${Math.round(value * 1000)} ms`;
  return `${value.toFixed(2)} s`;
}

export default function RapidApply() {
  const queryClient = useQueryClient();
  const [isRunning, setIsRunning] = useState(false);
  const [lastCycleSummary, setLastCycleSummary] = useState<string | null>(null);

  const { data: settings } = useQuery({ queryKey: ["rapid-apply-settings"], queryFn: getRapidApplySettings });
  const { data: stats } = useQuery({ queryKey: ["rapid-apply-stats"], queryFn: getRapidApplyStats });
  const { data: queue, isLoading: queueLoading } = useQuery({
    queryKey: ["rapid-apply-queue"],
    queryFn: listRapidApplyQueue,
  });

  const refreshAll = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["rapid-apply-settings"] }),
      queryClient.invalidateQueries({ queryKey: ["rapid-apply-stats"] }),
      queryClient.invalidateQueries({ queryKey: ["rapid-apply-queue"] }),
      queryClient.invalidateQueries({ queryKey: ["applications"] }),
    ]);
  };

  const handleToggle = async () => {
    if (!settings) return;
    await updateRapidApplySettings({ rapid_apply_enabled: !settings.rapid_apply_enabled });
    await refreshAll();
  };

  const handleMinScoreChange = async (value: number) => {
    await updateRapidApplySettings({ min_match_score_to_apply: value });
    await refreshAll();
  };

  const handleRunCycle = async () => {
    setIsRunning(true);
    try {
      const result = await runRapidApplyCycle();
      const rulesSuffix =
        result.detection.skipped_by_automation_rules > 0
          ? ` ${result.detection.skipped_by_automation_rules} skipped by automation rules/limits.`
          : "";
      setLastCycleSummary(
        `Detected ${result.detection.jobs_detected} new job(s), queued ${result.detection.queued}, ` +
          `processed ${result.processed} (${result.completed} completed, ${result.failed} failed).${rulesSuffix}`
      );
      await refreshAll();
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="space-y-6 p-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold">
            <Zap size={20} className="text-brand-600" /> Rapid Apply
          </h1>
          <p className="text-sm text-slate-500">
            Watches for new jobs, screens them against your profile, and queues the strongest matches by
            priority (P0 highest) for fast application.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm font-medium">
            <input
              type="checkbox"
              checked={settings?.rapid_apply_enabled ?? false}
              onChange={handleToggle}
              className="h-4 w-4 rounded border-slate-300"
            />
            Rapid Apply enabled
          </label>
          <button
            onClick={handleRunCycle}
            disabled={isRunning}
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
          >
            <Play size={15} className={isRunning ? "animate-pulse" : ""} />
            {isRunning ? "Running cycle..." : "Run cycle now"}
          </button>
        </div>
      </div>

      {lastCycleSummary && (
        <div className="rounded-lg bg-brand-50 p-3 text-sm text-brand-700 dark:bg-brand-900/30 dark:text-brand-200">
          {lastCycleSummary}
        </div>
      )}

      <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center gap-3 text-sm">
          <span className="font-medium">Minimum match score to auto-queue</span>
          <input
            type="number"
            min={0}
            max={100}
            value={settings?.min_match_score_to_apply ?? 60}
            onChange={(e) => handleMinScoreChange(Number(e.target.value))}
            className="w-20 rounded-lg border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-800"
          />
          <span className="text-slate-400">
            Jobs scoring below this never enter the queue, regardless of eligibility.
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {[
          { label: "Total screened", value: stats?.total_queued ?? "—" },
          { label: "Queued", value: stats?.queued ?? "—" },
          { label: "Processing", value: stats?.processing ?? "—" },
          { label: "Completed", value: stats?.completed ?? "—" },
          { label: "Skipped", value: stats?.skipped ?? "—" },
          { label: "Failed", value: stats?.failed ?? "—" },
        ].map((card) => (
          <div
            key={card.label}
            className="rounded-xl border border-slate-200 bg-white p-4 text-center dark:border-slate-800 dark:bg-slate-900"
          >
            <div className="text-2xl font-semibold">{card.value}</div>
            <div className="text-xs uppercase tracking-wide text-slate-400">{card.label}</div>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
          <Gauge size={15} /> Latency (spec section 58)
        </h2>
        <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          <div>
            <div className="text-xs text-slate-400">Detection → Match</div>
            <div className="font-medium">{formatSeconds(stats?.latency.avg_detection_to_match_seconds ?? null)}</div>
          </div>
          <div>
            <div className="text-xs text-slate-400">Match → Queued</div>
            <div className="font-medium">{formatSeconds(stats?.latency.avg_match_to_queue_seconds ?? null)}</div>
          </div>
          <div>
            <div className="text-xs text-slate-400">Application prep</div>
            <div className="font-medium">{formatSeconds(stats?.latency.avg_application_seconds ?? null)}</div>
          </div>
          <div>
            <div className="text-xs text-slate-400">Fastest end-to-end</div>
            <div className="font-medium">{formatSeconds(stats?.latency.fastest_total_seconds ?? null)}</div>
          </div>
        </div>
        {stats?.latency.count === 0 && (
          <p className="mt-2 text-xs text-slate-400">
            No completed queue entries yet — run a cycle to generate latency data.
          </p>
        )}
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Queue</h2>
        {queueLoading && <p className="text-sm text-slate-500">Loading queue...</p>}
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-100 text-xs uppercase tracking-wide text-slate-400 dark:border-slate-800">
              <tr>
                <th className="px-4 py-3">Priority</th>
                <th className="px-4 py-3">Job</th>
                <th className="px-4 py-3">Score</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Queued</th>
                <th className="px-4 py-3">Application</th>
              </tr>
            </thead>
            <tbody>
              {queue?.map((entry) => (
                <tr key={entry.id} className="border-b border-slate-50 last:border-0 dark:border-slate-800/60">
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${PRIORITY_COLORS[entry.priority]}`}>
                      {PRIORITY_LABELS[entry.priority]}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <Link to={`/jobs/${entry.job.id}`} className="font-medium hover:text-brand-600">
                      {entry.job.title}
                    </Link>
                    <div className="text-xs text-slate-400">{entry.job.company.name}</div>
                  </td>
                  <td className="px-4 py-3">{entry.match_score}%</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${
                        STATUS_COLORS[entry.status] ?? "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {entry.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {entry.queued_at ? new Date(entry.queued_at).toLocaleString() : "—"}
                  </td>
                  <td className="px-4 py-3">
                    {entry.application_id ? (
                      <Link to={`/applications/${entry.application_id}`} className="text-brand-600 hover:underline">
                        View application
                      </Link>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {queue?.length === 0 && (
            <div className="p-8 text-center text-sm text-slate-400">
              Nothing in the queue yet. Enable Rapid Apply, make sure your profile has some skills set,
              and click "Run cycle now" — or publish a mock job via the API to test the pipeline.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
