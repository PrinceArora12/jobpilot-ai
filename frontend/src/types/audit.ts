export interface AuditLogEntry {
  id: string;
  action: string;
  detail: string | null;
  ip_address: string | null;
  created_at: string;
}
