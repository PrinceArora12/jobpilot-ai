import type { Job } from "./job";

export interface JobMatch {
  id: string;
  job_id: string;
  job: Job;
  overall_score: number;
  skills_score: number;
  education_score: number;
  experience_score: number;
  location_score: number;
  role_score: number;
  matched_skills: string[];
  missing_skills: string[];
  explanation: string | null;
  is_eligible: boolean;
  eligibility_reasons: string[];
  created_at: string;
}
