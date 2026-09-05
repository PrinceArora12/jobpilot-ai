export interface FunnelStage {
  name: string;
  count: number;
}

export interface Funnel {
  total_applications: number;
  stages: FunnelStage[];
  submitted_rate: number | null;
  response_rate: number | null;
  interview_rate: number | null;
  offer_rate: number | null;
}

export interface ResumePerformance {
  resume_id: string;
  label: string;
  total_applications: number;
  submitted: number;
  responses: number;
  interviews: number;
  offers: number;
  avg_match_score: number | null;
  response_rate: number | null;
}

export interface TimelinePoint {
  date: string;
  discovered: number;
  submitted: number;
}

export interface AnalyticsSummary {
  total_applications: number;
  total_submitted: number;
  total_interviews: number;
  total_offers: number;
  avg_match_score: number | null;
  avg_days_to_submit: number | null;
}
