import { api } from "./api";
import type { Resume } from "@/types/resume";

export async function fetchResumes(): Promise<Resume[]> {
  const { data } = await api.get<Resume[]>("/resumes");
  return data;
}

export async function uploadResume(file: File, label: string): Promise<Resume> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post<Resume>(
    `/resumes?label=${encodeURIComponent(label)}`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data;
}

export async function setPrimaryResume(id: string): Promise<Resume> {
  const { data } = await api.put<Resume>(`/resumes/${id}`, { is_primary: true });
  return data;
}

export async function renameResume(id: string, label: string): Promise<Resume> {
  const { data } = await api.put<Resume>(`/resumes/${id}`, { label });
  return data;
}

export async function deleteResume(id: string): Promise<void> {
  await api.delete(`/resumes/${id}`);
}
