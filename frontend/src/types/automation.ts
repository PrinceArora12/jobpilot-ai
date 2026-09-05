export const AUTOMATION_STATES = ["running", "paused", "stopped"] as const;
export type AutomationState = (typeof AUTOMATION_STATES)[number];

export interface AutomationRule {
  state: AutomationState;
  max_applications_per_hour: number | null;
  max_applications_per_day: number | null;
  max_applications_per_company: number | null;
  blocked_sources: string[];
  blocked_companies: string[];
  blocked_keywords: string[];
}

export interface AutomationRuleUpdate {
  max_applications_per_hour?: number | null;
  max_applications_per_day?: number | null;
  max_applications_per_company?: number | null;
  blocked_sources?: string[];
  blocked_companies?: string[];
  blocked_keywords?: string[];
}

export interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  application_id: string | null;
  created_at: string;
}
