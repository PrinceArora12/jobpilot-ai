import { useQuery } from "@tanstack/react-query";
import { BarChart3 } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { getAnalyticsSummary, getFunnel, getResumePerformance, getTimeline } from "@/services/analytics";

const FUNNEL_LABELS: Record<string, string> = {
  discovered: "Discovered",
  matched: "Matched",
  saved: "Saved",
  preparing: "Preparing",
  ready_for_review: "Ready for review",
  submitted: "Submitted",
  assessment: "Assessment",
  interview: "Interview",
  offer: "Offer",
};

const FUNNEL_COLORS = ["#4f46e5", "#6366f1", "#818cf8", "#a5b4fc", "#c7d2fe", "#059669", "#10b981", "#34d399", "#facc15"];

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 text-center dark:border-slate-800 dark:bg-slate-900">
      <div className="text-2xl font-semibold">{value}</div>
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
    </div>
  );
}

function RateCard({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="text-xl font-semibold">{value === null ? "—" : `${value}%`}</div>
      <div className="text-xs text-slate-400">{label}</div>
    </div>
  );
}

export default function Analytics() {
  const { data: summary } = useQuery({ queryKey: ["analytics-summary"], queryFn: getAnalyticsSummary });
  const { data: funnel } = useQuery({ queryKey: ["analytics-funnel"], queryFn: getFunnel });
  const { data: resumePerf } = useQuery({
    queryKey: ["analytics-resume-performance"],
    queryFn: getResumePerformance,
  });
  const { data: timeline } = useQuery({
    queryKey: ["analytics-timeline"],
    queryFn: () => getTimeline(30),
  });

  const funnelChartData = funnel?.stages.map((s) => ({ name: FUNNEL_LABELS[s.name] ?? s.name, count: s.count })) ?? [];

  return (
    <div className="space-y-6 p-8">
      <div>
        <h1 className="flex items-center gap-2 text-xl font-semibold">
          <BarChart3 size={20} className="text-brand-600" /> Analytics
        </h1>
        <p className="text-sm text-slate-500">
          How far applications get through the pipeline, how quickly, and which resume performs best (spec
          section 11).
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <StatCard label="Total applications" value={summary?.total_applications ?? "—"} />
        <StatCard label="Submitted" value={summary?.total_submitted ?? "—"} />
        <StatCard label="Interviews" value={summary?.total_interviews ?? "—"} />
        <StatCard label="Offers" value={summary?.total_offers ?? "—"} />
        <StatCard
          label="Avg match score"
          value={summary?.avg_match_score != null ? `${summary.avg_match_score}%` : "—"}
        />
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Application funnel
        </h2>
        <p className="mb-4 text-xs text-slate-400">
          Counts every application that ever reached each stage — even if it was later rejected — so this
          shows how far applications got, not just where they ended up.
        </p>
        {funnel?.total_applications === 0 ? (
          <p className="py-8 text-center text-sm text-slate-400">
            No applications yet — the funnel will fill in as you track jobs.
          </p>
        ) : (
          <div style={{ width: "100%", height: 280 }}>
            <ResponsiveContainer>
              <BarChart data={funnelChartData} layout="vertical" margin={{ left: 24 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" allowDecimals={false} />
                <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                  {funnelChartData.map((_, i) => (
                    <Cell key={i} fill={FUNNEL_COLORS[i % FUNNEL_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <RateCard label="Submitted rate" value={funnel?.submitted_rate ?? null} />
          <RateCard label="Response rate" value={funnel?.response_rate ?? null} />
          <RateCard label="Interview rate" value={funnel?.interview_rate ?? null} />
          <RateCard label="Offer rate" value={funnel?.offer_rate ?? null} />
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Applications over time
        </h2>
        <p className="mb-4 text-xs text-slate-400">Last 30 days — jobs discovered vs. applications submitted.</p>
        <div style={{ width: "100%", height: 240 }}>
          <ResponsiveContainer>
            <LineChart data={timeline ?? []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11 }}
                tickFormatter={(d: string) => d.slice(5)}
                interval={Math.max(0, Math.floor((timeline?.length ?? 30) / 8))}
              />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line type="monotone" dataKey="discovered" stroke="#6366f1" strokeWidth={2} dot={false} name="Discovered" />
              <Line type="monotone" dataKey="submitted" stroke="#10b981" strokeWidth={2} dot={false} name="Submitted" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Resume performance
        </h2>
        {!resumePerf || resumePerf.length === 0 ? (
          <p className="text-sm text-slate-400">
            No applications with a resume attached yet — attach a resume when tracking an application to
            see how each version performs.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-100 text-xs uppercase tracking-wide text-slate-400 dark:border-slate-800">
                <tr>
                  <th className="px-3 py-2">Resume</th>
                  <th className="px-3 py-2">Applications</th>
                  <th className="px-3 py-2">Submitted</th>
                  <th className="px-3 py-2">Interviews</th>
                  <th className="px-3 py-2">Offers</th>
                  <th className="px-3 py-2">Response rate</th>
                  <th className="px-3 py-2">Avg match score</th>
                </tr>
              </thead>
              <tbody>
                {resumePerf.map((r) => (
                  <tr key={r.resume_id} className="border-b border-slate-50 last:border-0 dark:border-slate-800/60">
                    <td className="px-3 py-2 font-medium">{r.label}</td>
                    <td className="px-3 py-2">{r.total_applications}</td>
                    <td className="px-3 py-2">{r.submitted}</td>
                    <td className="px-3 py-2">{r.interviews}</td>
                    <td className="px-3 py-2">{r.offers}</td>
                    <td className="px-3 py-2">{r.response_rate != null ? `${r.response_rate}%` : "—"}</td>
                    <td className="px-3 py-2">{r.avg_match_score != null ? `${r.avg_match_score}%` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
