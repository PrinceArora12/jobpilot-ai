import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Bookmark, BookmarkCheck, Building2, Calendar, MapPin, Sparkles, Wand2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { applyResumeTailoring, previewResumeTailoring } from "@/services/assistant";
import { createApplication, listApplications } from "@/services/applications";
import { fetchJob } from "@/services/jobs";
import { computeMatch, getMatchForJob } from "@/services/matches";
import { fetchResumes } from "@/services/resumes";
import type { TailorPreview } from "@/types/assistant";

export default function JobDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isMatching, setIsMatching] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const { data: job, isLoading } = useQuery({
    queryKey: ["job", id],
    queryFn: () => fetchJob(id!),
    enabled: !!id,
  });
  const { data: match, refetch: refetchMatch } = useQuery({
    queryKey: ["match", id],
    queryFn: () => getMatchForJob(id!),
    enabled: !!id,
  });
  const { data: applications } = useQuery({ queryKey: ["applications"], queryFn: () => listApplications() });
  const existingApplication = applications?.find((a) => a.job_id === id);
  const { data: resumes } = useQuery({ queryKey: ["resumes"], queryFn: fetchResumes });
  const primaryResume = resumes?.find((r) => r.is_primary) ?? resumes?.[0];

  const [tailorPreview, setTailorPreview] = useState<TailorPreview | null>(null);
  const [isTailoring, setIsTailoring] = useState(false);
  const [isApplyingTailor, setIsApplyingTailor] = useState(false);
  const [tailorApplied, setTailorApplied] = useState(false);

  const handleSave = async () => {
    if (!id) return;
    setIsSaving(true);
    try {
      const application = await createApplication(id, match ? "matched" : "discovered");
      await queryClient.invalidateQueries({ queryKey: ["applications"] });
      navigate(`/applications/${application.id}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleComputeMatch = async () => {
    if (!id) return;
    setIsMatching(true);
    try {
      await computeMatch(id);
      await refetchMatch();
      await queryClient.invalidateQueries({ queryKey: ["matches"] });
    } finally {
      setIsMatching(false);
    }
  };

  const handlePreviewTailoring = async () => {
    if (!id || !primaryResume) return;
    setIsTailoring(true);
    setTailorApplied(false);
    try {
      const preview = await previewResumeTailoring(primaryResume.id, id);
      setTailorPreview(preview);
    } finally {
      setIsTailoring(false);
    }
  };

  const handleApplyTailoring = async () => {
    if (!primaryResume || !tailorPreview) return;
    setIsApplyingTailor(true);
    try {
      await applyResumeTailoring(primaryResume.id, tailorPreview.suggested_order);
      await queryClient.invalidateQueries({ queryKey: ["resumes"] });
      setTailorApplied(true);
    } finally {
      setIsApplyingTailor(false);
    }
  };

  if (isLoading || !job) {
    return <div className="p-8 text-sm text-slate-500">Loading job...</div>;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-8">
      <Link to="/jobs" className="flex items-center gap-1 text-sm text-slate-500 hover:text-brand-600">
        <ArrowLeft size={14} /> Back to jobs
      </Link>

      <div className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold">{job.title}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-slate-500">
              <span className="flex items-center gap-1">
                <Building2 size={14} /> {job.company.name}
              </span>
              {job.location && (
                <span className="flex items-center gap-1">
                  <MapPin size={14} /> {job.location}
                </span>
              )}
              {job.deadline && (
                <span className="flex items-center gap-1">
                  <Calendar size={14} /> Deadline {new Date(job.deadline).toLocaleDateString()}
                </span>
              )}
            </div>
          </div>
          <div className="flex flex-wrap gap-1.5">
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

        <div className="mt-4 rounded-lg border border-slate-100 p-4 dark:border-slate-800">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              AI Match
            </h2>
            <button
              onClick={handleComputeMatch}
              disabled={isMatching}
              className="flex items-center gap-1 rounded-lg bg-brand-50 px-2.5 py-1.5 text-xs font-medium text-brand-700 hover:bg-brand-100 disabled:opacity-60 dark:bg-brand-900/30 dark:text-brand-200"
            >
              <Sparkles size={13} /> {match ? "Recompute" : "Compute match"}
            </button>
          </div>
          {match ? (
            <div className="mt-3 space-y-2">
              <div className="text-2xl font-semibold">{match.overall_score}% match</div>
              <div className="grid grid-cols-2 gap-2 text-xs text-slate-500 sm:grid-cols-5">
                <div>Skills: {match.skills_score}%</div>
                <div>Education: {match.education_score}%</div>
                <div>Experience: {match.experience_score}%</div>
                <div>Location: {match.location_score}%</div>
                <div>Role: {match.role_score}%</div>
              </div>
              {match.explanation && <p className="text-sm text-slate-600 dark:text-slate-300">{match.explanation}</p>}
              {!match.is_eligible && (
                <div className="rounded-lg bg-amber-50 p-2 text-xs text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                  Fails fast eligibility: {match.eligibility_reasons.join("; ")}
                </div>
              )}
            </div>
          ) : (
            <p className="mt-2 text-sm text-slate-400">Not yet scored against your profile.</p>
          )}
        </div>

        <div className="mt-4 rounded-lg border border-slate-100 p-4 dark:border-slate-800">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              Tailor my resume
            </h2>
            <button
              onClick={handlePreviewTailoring}
              disabled={isTailoring || !primaryResume}
              title={primaryResume ? "Preview reordering your resume's skills for this job" : "Upload a resume first"}
              className="flex items-center gap-1 rounded-lg bg-brand-50 px-2.5 py-1.5 text-xs font-medium text-brand-700 hover:bg-brand-100 disabled:opacity-60 dark:bg-brand-900/30 dark:text-brand-200"
            >
              <Wand2 size={13} /> {isTailoring ? "Analyzing..." : "Preview tailoring"}
            </button>
          </div>
          {!primaryResume && (
            <p className="mt-2 text-sm text-slate-400">Upload a resume to tailor it for this job.</p>
          )}
          {tailorPreview && (
            <div className="mt-3 space-y-3 text-sm">
              {tailorPreview.changed ? (
                <>
                  <p className="text-slate-500">
                    This only reorders skills your resume already lists — nothing is added or removed.
                  </p>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <div>
                      <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">
                        Current order
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {tailorPreview.original_order.map((skill) => (
                          <span
                            key={skill}
                            className="rounded-full border border-slate-200 px-2 py-0.5 text-xs text-slate-500 dark:border-slate-700"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">
                        Suggested order
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {tailorPreview.suggested_order.map((skill) => (
                          <span
                            key={skill}
                            className={`rounded-full px-2 py-0.5 text-xs ${
                              tailorPreview.matched_keywords.includes(skill)
                                ? "bg-emerald-50 font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
                                : "border border-slate-200 text-slate-500 dark:border-slate-700"
                            }`}
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                  {tailorApplied ? (
                    <p className="text-emerald-600 dark:text-emerald-400">Applied to your resume.</p>
                  ) : (
                    <button
                      onClick={handleApplyTailoring}
                      disabled={isApplyingTailor}
                      className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 disabled:opacity-60"
                    >
                      {isApplyingTailor ? "Applying..." : "Approve & apply"}
                    </button>
                  )}
                </>
              ) : (
                <p className="text-slate-500">Your resume's skill order already matches this job well.</p>
              )}
            </div>
          )}
        </div>

        {job.salary && (
          <div className="mt-4 text-sm">
            <span className="font-medium">Salary/stipend: </span>
            {job.salary}
          </div>
        )}

        <div className="mt-6">
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Description
          </h2>
          <p className="whitespace-pre-line text-sm text-slate-700 dark:text-slate-300">
            {job.description || "No description provided."}
          </p>
        </div>

        {job.requirements.length > 0 && (
          <div className="mt-6">
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
              Requirements
            </h2>
            <ul className="list-inside list-disc text-sm text-slate-700 dark:text-slate-300">
              {job.requirements.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </div>
        )}

        {job.skills.length > 0 && (
          <div className="mt-6">
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Skills</h2>
            <div className="flex flex-wrap gap-1.5">
              {job.skills.map((skill) => (
                <span
                  key={skill}
                  className="rounded-full border border-slate-200 px-2 py-0.5 text-xs text-slate-600 dark:border-slate-700 dark:text-slate-300"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="mt-6 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
          {existingApplication ? (
            <Link
              to={`/applications/${existingApplication.id}`}
              className="flex items-center gap-2 rounded-lg bg-brand-50 px-4 py-2 text-sm font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-200"
            >
              <BookmarkCheck size={15} /> Tracking this application
            </Link>
          ) : (
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
            >
              <Bookmark size={15} /> {isSaving ? "Saving..." : "Save / Track application"}
            </button>
          )}
          <a
            href={job.url}
            target="_blank"
            rel="noreferrer"
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            Open original listing
          </a>
          <span className="self-center text-xs text-slate-400">
            Source: {job.source} · First seen {new Date(job.first_seen_at).toLocaleString()}
          </span>
        </div>
      </div>
    </div>
  );
}
