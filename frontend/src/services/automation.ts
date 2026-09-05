import { api } from "./api";
import type { AutomationRule, AutomationRuleUpdate, Notification } from "@/types/automation";

export async function getAutomationRules(): Promise<AutomationRule> {
  const { data } = await api.get<AutomationRule>("/automation/rules");
  return data;
}

export async function updateAutomationRules(payload: AutomationRuleUpdate): Promise<AutomationRule> {
  const { data } = await api.put<AutomationRule>("/automation/rules", payload);
  return data;
}

export async function startAutomation(): Promise<AutomationRule> {
  const { data } = await api.post<AutomationRule>("/automation/start");
  return data;
}

export async function pauseAutomation(): Promise<AutomationRule> {
  const { data } = await api.post<AutomationRule>("/automation/pause");
  return data;
}

export async function stopAutomation(): Promise<AutomationRule> {
  const { data } = await api.post<AutomationRule>("/automation/stop");
  return data;
}

export async function listNotifications(unreadOnly = false): Promise<Notification[]> {
  const { data } = await api.get<Notification[]>("/notifications", { params: { unread_only: unreadOnly } });
  return data;
}

export async function getUnreadNotificationCount(): Promise<number> {
  const { data } = await api.get<{ unread_count: number }>("/notifications/unread-count");
  return data.unread_count;
}

export async function markNotificationRead(id: string): Promise<Notification> {
  const { data } = await api.post<Notification>(`/notifications/${id}/read`);
  return data;
}

export async function markAllNotificationsRead(): Promise<number> {
  const { data } = await api.post<{ marked_read: number }>("/notifications/read-all");
  return data.marked_read;
}
