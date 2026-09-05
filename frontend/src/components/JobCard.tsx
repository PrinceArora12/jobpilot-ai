import { Building2, Clock, MapPin } from "lucide-react";
import { Link } from "react-router-dom";

import type { Job } from "@/types/job";
import type { JobMatch } from "@/types/match";

function scoreColor(score: number): string {
  if (score >= 85) return "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300";
  if (score >= 60) return "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300";
  return "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300";
}

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function JobCard({ job, match }: { job: Job; match?: JobMatch }) {
  const missingSet = new Set((match?.missing_skills ?? []).map((s) => s.toLowerCase()));

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 transition-shadow hover:shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-start justify-between">
        <div>
          <Link to={`/jobs/${job.id}`} className="font-medium hover:text-brand-600">
            {job.title}
          </Link>
          <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-slate-500">
            <span className="flex items-center gap-1">
              <Building2 size={14} /> {job.company.name}
            </span>
            {job.location && (
              <span className="flex items-center gap-1">
                <MapPin size={14} /> {job.location}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Clock size={14} /> Posted {timeAgo(job.posted_at)}
            </span>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {match && (
            <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${scoreColor(match.overall_score)}`}>
              {match.overall_score}% match
            </span>
          )}
          {job.remote && (
            <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
              Remote
            </span>
          )}
          {job.employment_type && (
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium capitalize text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              {job.employment_type.replace(/_/g, " ")}
            </span>
          )}
        </div>
      </div>

      {job.skills.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {job.skills.map((skill) => {
            const isMissing = match && missingSet.has(skill.toLowerCase());
            const isMatched = match && !isMissing;
            return (
              <span
                key={skill}
                className={`rounded-full border px-2 py-0.5 text-xs ${
                  isMatched
                    ? "border-emerald-200 text-emerald-700 dark:border-emerald-800 dark:text-emerald-300"
                    : isMissing
                      ? "border-red-200 text-red-600 dark:border-red-900 dark:text-red-400"
                      : "border-slate-200 text-slate-600 dark:border-slate-700 dark:text-slate-300"
                }`}
              >
                {skill} {isMatched ? "✓" : isMissing ? "✕" : ""}
              </span>
            );
          })}
        </div>
      )}

      <div className="mt-4 flex gap-2">
        <Link
          to={`/jobs/${job.id}`}
          className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700"
        >
          View
        </Link>
        <a
          href={job.url}
          target="_blank"
          rel="noreferrer"
          className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          Open original listing
        </a>
      </div>
    </div>
  );
}
