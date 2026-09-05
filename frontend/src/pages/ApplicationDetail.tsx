import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, RefreshCw, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  addApplicationNote,
  autoSubmitApplication,
  getApplication,
  updateApplicationStatus,
} from "@/services/applications";
import { askAssistant } from "@/services/assistant";
import { APPLICATION_STATUSES } from "@/types/application";
import type { AssistantAnswer } from "@/types/assistant";

export default function ApplicationDetail() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [note, setNote] = useState("");
  const [isSavingNote, setIsSavingNote] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [question, setQuestion] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [assistantAnswer, setAssistantAnswer] = useState<AssistantAnswer | null>(null);

  const { data: application, isLoading } = useQuery({
    queryKey: ["application", id],
    queryFn: () => getApplication(id!),
    enabled: !!id,
  });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["application", id] });

  const handleStatusChange = async (status: string) => {
    if (!id) return;
    await updateApplicationStatus(id, status);
    await refresh();
    await queryClient.invalidateQueries({ queryKey: ["applications"] });
  };

  const handleRetryAutomation = async () => {
    setIsRetrying(true);
    try {
      await autoSubmitApplication(id!);
      await refresh();
      await queryClient.invalidateQueries({ queryKey: ["applications"] });
    } finally {
      setIsRetrying(false);
    }
  };

  const handleAskAssistant = async () => {
    if (!id || !question.trim()) return;
    setIsAsking(true);
    try {
      const result = await askAssistant(id, question.trim());
      setAssistantAnswer(result);
    } finally {
      setIsAsking(false);
    }
  };

  const handleAddNote = async () => {
    if (!id || !note.trim()) return;
    setIsSavingNote(true);
    try {
      await addApplicationNote(id, note.trim());
      setNote("");
      await refresh();
    } finally {
      setIsSavingNote(false);
    }
  };

  if (isLoading || !application) {
    return <div className="p-8 text-sm text-slate-500">Loading application...</div>;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-8">
      <Link to="/applications" className="flex items-center gap-1 text-sm text-slate-500 hover:text-brand-600">
        <ArrowLeft size={14} /> Back to applications
      </Link>

      <div className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold">{application.job.title}</h1>
            <p className="text-sm text-slate-500">
              {application.job.company.name}
              {application.job.location ? ` · ${application.job.location}` : ""}
            </p>
          </div>
          <Link
            to={`/jobs/${application.job.id}`}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300"
          >
            View job
          </Link>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <label className="text-sm font-medium">Status</label>
          <select
            value={application.status}
            onChange={(e) => handleStatusChange(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm capitalize dark:border-slate-700 dark:bg-slate-800"
          >
            {APPLICATION_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, " ")}
              </option>
            ))}
          </select>
          {application.match_score !== null && (
            <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-semibold text-brand-700 dark:bg-brand-900/30 dark:text-brand-200">
              {application.match_score}% match
            </span>
          )}
          {application.status === "needs_manual_review" && (
            <button
              onClick={handleRetryAutomation}
              disabled={isRetrying}
              title="Re-run browser automation now that you may have fixed what stopped it"
              className="ml-auto flex items-center gap-1.5 rounded-lg border border-orange-200 bg-orange-50 px-3 py-1.5 text-xs font-medium text-orange-700 hover:bg-orange-100 disabled:opacity-60 dark:border-orange-900 dark:bg-orange-900/30 dark:text-orange-200"
            >
              <RefreshCw size={13} className={isRetrying ? "animate-spin" : ""} />
              {isRetrying ? "Retrying..." : "Retry automation"}
            </button>
          )}
        </div>

        <div className="mt-6">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Timeline</h2>
          <div className="space-y-3">
            {application.events.map((event) => (
              <div key={event.id} className="border-l-2 border-slate-200 pl-3 dark:border-slate-700">
                <div className="text-xs text-slate-400">
                  {new Date(event.created_at).toLocaleString()} · {event.event_type.replace(/_/g, " ")}
                </div>
                <div className="text-sm text-slate-700 dark:text-slate-300">{event.message}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-6 border-t border-slate-100 pt-4 dark:border-slate-800">
          <h2 className="mb-2 flex items-center gap-1.5 text-sm font-semibold uppercase tracking-wide text-slate-500">
            <Sparkles size={14} /> Ask the assistant
          </h2>
          <p className="mb-2 text-xs text-slate-400">
            Paste a screening question — answers are grounded only in your profile/resume, never fabricated.
          </p>
          <div className="flex gap-2">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. Do you have experience with Python?"
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
            />
            <button
              onClick={handleAskAssistant}
              disabled={isAsking || !question.trim()}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {isAsking ? "Thinking..." : "Get answer"}
            </button>
          </div>
          {assistantAnswer && (
            <div className="mt-3 rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-700">
              {assistantAnswer.status === "answered" ? (
                <>
                  <p>{assistantAnswer.answer}</p>
                  <p className="mt-1 text-xs text-slate-400">
                    Confidence {Math.round((assistantAnswer.confidence ?? 0) * 100)}% · Source:{" "}
                    {assistantAnswer.source}
                  </p>
                </>
              ) : (
                <p className="text-amber-700 dark:text-amber-300">
                  Needs your input — {assistantAnswer.reason}
                </p>
              )}
            </div>
          )}
        </div>

        <div className="mt-6 border-t border-slate-100 pt-4 dark:border-slate-800">
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Add a note</h2>
          <div className="flex gap-2">
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. Followed up with recruiter on LinkedIn"
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
            />
            <button
              onClick={handleAddNote}
              disabled={isSavingNote || !note.trim()}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
            >
              Add
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
