import { api } from "./api";
import type { JobMatch } from "@/types/match";

export async function listMatches(): Promise<JobMatch[]> {
  const { data } = await api.get<JobMatch[]>("/matches");
  return data;
}

export async function computeAllMatches(): Promise<JobMatch[]> {
  const { data } = await api.post<JobMatch[]>("/matches/compute-all");
  return data;
}

export async function computeMatch(jobId: string): Promise<JobMatch> {
  const { data } = await api.post<JobMatch>(`/matches/compute/${jobId}`);
  return data;
}

export async function getMatchForJob(jobId: string): Promise<JobMatch | null> {
  try {
    const { data } = await api.get<JobMatch>(`/matches/${jobId}`);
    return data;
  } catch {
    return null;
  }
}
