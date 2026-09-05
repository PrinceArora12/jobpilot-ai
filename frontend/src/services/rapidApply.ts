import { api } from "./api";
import type { CycleResult, RapidApplyQueueEntry, RapidApplySettings, RapidApplyStats } from "@/types/rapidApply";

export async function getRapidApplySettings(): Promise<RapidApplySettings> {
  const { data } = await api.get<RapidApplySettings>("/rapid-apply/settings");
  return data;
}

export async function updateRapidApplySettings(
  payload: Partial<RapidApplySettings>
): Promise<RapidApplySettings> {
  const { data } = await api.put<RapidApplySettings>("/rapid-apply/settings", payload);
  return data;
}

export async function runRapidApplyCycle(): Promise<CycleResult> {
  const { data } = await api.post<CycleResult>("/rapid-apply/run-cycle");
  return data;
}

export async function listRapidApplyQueue(): Promise<RapidApplyQueueEntry[]> {
  const { data } = await api.get<RapidApplyQueueEntry[]>("/rapid-apply/queue");
  return data;
}

export async function getRapidApplyStats(): Promise<RapidApplyStats> {
  const { data } = await api.get<RapidApplyStats>("/rapid-apply/stats");
  return data;
}
