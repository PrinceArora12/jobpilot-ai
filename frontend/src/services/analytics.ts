import { api } from "./api";
import type { AnalyticsSummary, Funnel, ResumePerformance, TimelinePoint } from "@/types/analytics";

export async function getAnalyticsSummary(): Promise<AnalyticsSummary> {
  const { data } = await api.get<AnalyticsSummary>("/analytics/summary");
  return data;
}

export async function getFunnel(): Promise<Funnel> {
  const { data } = await api.get<Funnel>("/analytics/funnel");
  return data;
}

export async function getResumePerformance(): Promise<ResumePerformance[]> {
  const { data } = await api.get<ResumePerformance[]>("/analytics/resume-performance");
  return data;
}

export async function getTimeline(days = 30): Promise<TimelinePoint[]> {
  const { data } = await api.get<TimelinePoint[]>("/analytics/timeline", { params: { days } });
  return data;
}
