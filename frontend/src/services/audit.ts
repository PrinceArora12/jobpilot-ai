import { api } from "./api";
import type { AuditLogEntry } from "@/types/audit";

export async function getAuditLog(limit = 100): Promise<AuditLogEntry[]> {
  const { data } = await api.get<AuditLogEntry[]>("/audit-log", { params: { limit } });
  return data;
}
