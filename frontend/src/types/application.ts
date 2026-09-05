import type { Job } from "./job";

export interface ApplicationEvent {
  id: string;
  event_type: string;
  message: string;
  created_at: string;
}

export interface Application {
  id: string;
  job_id: string;
  job: Job;
  resume_id: string | null;
  status: string;
  match_score: number | null;
  notes: string | null;
  discovered_at: string;
  applied_at: string | null;
  events: ApplicationEvent[];
  created_at: string;
}

export const APPLICATION_STATUSES = [
  "discovered",
  "matched",
  "saved",
  "preparing",
  "ready_for_review",
  "needs_manual_review",
  "submitted",
  "assessment",
  "interview",
  "offer",
  "rejected",
  "withdrawn",
] as const;
