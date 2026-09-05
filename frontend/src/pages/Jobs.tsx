import { useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Search, Sparkles } from "lucide-react";
import { useState } from "react";

import JobCard from "@/components/JobCard";
import { searchJobs, syncMockJobs } from "@/services/jobs";
import { computeAllMatches, listMatches } from "@/services/matches";
import { EMPLOYMENT_TYPES } from "@/types/jobConstants";

export default function Jobs() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<{
    q: string;
    employment_type: string;
    remote: string;
  }>({ q: "", employment_type: "", remote: "" });
  const [isSyncing, setIsSyncing] = useState(false);
  const [isMatching, setIsMatching] = useState(false);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["jobs", filters],
    queryFn: () =>
      searchJobs({
        q: filters.q || undefined,
        employment_type: filters.employment_type || undefined,
        remote: filters.remote === "" ? undefined : filters.remote === "true",
      }),
  });

  const { data: matches, refetch: refetchMatches } = useQuery({
    queryKey: ["matches"],
    queryFn: listMatches,
  });
  const matchByJobId = new Map((matches ?? []).map((m) => [m.job_id, m]));

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      await syncMockJobs();
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
      await refetch();
    } finally {
      setIsSyncing(false);
    }
  };

  const handleComputeMatches = async () => {
    setIsMatching(true);
    try {
      await computeAllMatches();
      await refetchMatches();
    } finally {
      setIsMatching(false);
    }
  };

  return (
    <div className="space-y-6 p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Jobs</h1>
          <p className="text-sm text-slate-500">
            {data ? `${data.total} job${data.total === 1 ? "" : "s"} found` : "Loading..."}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleSync}
            disabled={isSyncing}
            title="Pull in any newly published mock jobs"
            className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-60 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <RefreshCw size={15} className={isSyncing ? "animate-spin" : ""} />
            Sync sources
          </button>
          <button
            onClick={handleComputeMatches}
            disabled={isMatching}
            title="Score every job against your profile"
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
          >
            <Sparkles size={15} />
            {isMatching ? "Matching..." : "Compute matches"}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
          <input
            value={filters.q}
            onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value }))}
            placeholder="Search title or description..."
            className="w-full rounded-lg border border-slate-300 py-2 pl-9 pr-3 text-sm dark:border-slate-700 dark:bg-slate-800"
          />
        </div>
        <select
          value={filters.employment_type}
          onChange={(e) => setFilters((f) => ({ ...f, employment_type: e.target.value }))}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
        >
          <option value="">All job types</option>
          {EMPLOYMENT_TYPES.map((type) => (
            <option key={type} value={type}>
              {type.replace(/_/g, " ")}
            </option>
          ))}
        </select>
        <select
          value={filters.remote}
          onChange={(e) => setFilters((f) => ({ ...f, remote: e.target.value }))}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
        >
          <option value="">Any work mode</option>
          <option value="true">Remote only</option>
          <option value="false">On-site/Hybrid</option>
        </select>
      </div>

      {isLoading && <p className="text-sm text-slate-500">Loading jobs...</p>}

      <div className="space-y-4">
        {data?.items.map((job) => (
          <JobCard key={job.id} job={job} match={matchByJobId.get(job.id)} />
        ))}
        {data?.items.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-400 dark:border-slate-700">
            No jobs match these filters yet. Try "Sync sources", or publish a mock job via the API to
            test the pipeline.
          </div>
        )}
      </div>
    </div>
  );
}
