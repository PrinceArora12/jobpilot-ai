import { api } from "./api";
import type { Resume } from "@/types/resume";
import type { AssistantAnswer, TailorPreview } from "@/types/assistant";

export async function askAssistant(applicationId: string, question: string): Promise<AssistantAnswer> {
  const { data } = await api.post<AssistantAnswer>("/assistant/answer", {
    application_id: applicationId,
    question,
  });
  return data;
}

export async function previewResumeTailoring(resumeId: string, jobId: string): Promise<TailorPreview> {
  const { data } = await api.post<TailorPreview>("/assistant/tailor-resume/preview", {
    resume_id: resumeId,
    job_id: jobId,
  });
  return data;
}

export async function applyResumeTailoring(resumeId: string, skillOrder: string[]): Promise<Resume> {
  const { data } = await api.post<Resume>("/assistant/tailor-resume/apply", {
    resume_id: resumeId,
    skill_order: skillOrder,
  });
  return data;
}
