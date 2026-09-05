import type { Job } from "./job";

export interface RapidApplySettings {
  rapid_apply_enabled: boolean;
  min_match_score_to_apply: number;
}

export interface RapidApplyQueueEntry {
  id: string;
  job: Job;
  match_score: number;
  priority: number;
  status: "queued" | "processing" | "completed" | "skipped" | "failed";
  failure_reason: string | null;
  application_id: string | null;
  source_posted_at: string | null;
  first_seen_at: string | null;
  detected_at: string | null;
  normalized_at: string | null;
  matched_at: string | null;
  queued_at: string | null;
  application_started_at: string | null;
  application_completed_at: string | null;
  created_at: string;
}

export interface DetectionResult {
  jobs_detected: number;
  evaluations: number;
  queued: number;
  skipped_ineligible: number;
  skipped_low_score: number;
  skipped_by_automation_rules: number;
  already_queued: number;
}

export interface CycleResult {
  detection: DetectionResult;
  processed: number;
  completed: number;
  failed: number;
}

export interface LatencyStats {
  count: number;
  avg_detection_to_match_seconds: number | null;
  avg_match_to_queue_seconds: number | null;
  avg_application_seconds: number | null;
  avg_total_seconds: number | null;
  fastest_total_seconds: number | null;
}

export interface RapidApplyStats {
  total_queued: number;
  queued: number;
  processing: number;
  completed: number;
  skipped: number;
  failed: number;
  queue_depth_by_priority: Record<string, number>;
  latency: LatencyStats;
}
