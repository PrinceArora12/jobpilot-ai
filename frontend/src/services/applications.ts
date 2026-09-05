import { api } from "./api";
import type { Application } from "@/types/application";

export async function listApplications(status?: string): Promise<Application[]> {
  const { data } = await api.get<Application[]>("/applications", {
    params: status ? { status } : undefined,
  });
  return data;
}

export async function getApplication(id: string): Promise<Application> {
  const { data } = await api.get<Application>(`/applications/${id}`);
  return data;
}

export async function createApplication(jobId: string, status = "discovered"): Promise<Application> {
  const { data } = await api.post<Application>("/applications", { job_id: jobId, status });
  return data;
}

export async function updateApplicationStatus(id: string, status: string): Promise<Application> {
  const { data } = await api.put<Application>(`/applications/${id}`, { status });
  return data;
}

export async function addApplicationNote(id: string, message: string): Promise<Application> {
  const { data } = await api.post<Application>(`/applications/${id}/notes`, { message });
  return data;
}

export async function autoSubmitApplication(id: string): Promise<Application> {
  const { data } = await api.post<Application>(`/applications/${id}/auto-submit`);
  return data;
}

export async function deleteApplication(id: string): Promise<void> {
  await api.delete(`/applications/${id}`);
}
