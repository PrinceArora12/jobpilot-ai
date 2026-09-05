export interface AssistantAnswer {
  status: "answered" | "needs_user_input";
  answer: string | null;
  confidence: number | null;
  source: string | null;
  reason: string | null;
}

export interface TailorPreview {
  original_order: string[];
  suggested_order: string[];
  matched_keywords: string[];
  changed: boolean;
}
