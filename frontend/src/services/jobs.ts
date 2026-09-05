import { api } from "./api";
import type { Job, JobFilters, JobListResponse } from "@/types/job";

export async function searchJobs(filters: JobFilters): Promise<JobListResponse> {
  const params: Record<string, string> = {};
  if (filters.q) params.q = filters.q;
  if (filters.employment_type) params.employment_type = filters.employment_type;
  if (filters.experience_level) params.experience_level = filters.experience_level;
  if (filters.remote !== undefined) params.remote = String(filters.remote);
  if (filters.location) params.location = filters.location;
  if (filters.source) params.source = filters.source;
  if (filters.skill) params.skill = filters.skill;
  if (filters.page) params.page = String(filters.page);

  const { data } = await api.get<JobListResponse>("/jobs", { params });
  return data;
}

export async function fetchJob(id: string): Promise<Job> {
  const { data } = await api.get<Job>(`/jobs/${id}`);
  return data;
}

export async function syncMockJobs(): Promise<Job[]> {
  const { data } = await api.post<Job[]>("/jobs/sync/mock");
  return data;
}
