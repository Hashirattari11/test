// Typed admin API helpers (admin-only endpoints under /admin/*).
import { request } from "./api";

export type AdminOverview = {
  total_users: number;
  total_repos: number;
  alerts_sent: number;
  alerts_pending: number;
  alerts_dismissed: number;
  test_alerts_sent: number;
  providers_monitored: number;
  providers_planned: number;
};

export type PendingAlert = {
  id: string;
  repo_id?: string | null;
  repo_name?: string | null;
  provider?: string | null;
  api_name?: string | null;
  customer_email?: string | null;
  confidence?: string | null;
  severity?: string | null;
  severity_reason?: string | null;
  evidence?: string | null;
  subject?: string | null;
  preview?: string | null;
  created_at?: string | null;
};

export type PendingAlertsResponse = {
  alerts: PendingAlert[];
};

export type ApproveRejectResponse = {
  ok: boolean;
  email_sent?: boolean;
  alert_id?: string;
  status?: string;
};

export type HealthRow = {
  id?: string;
  job_name: string;
  status: string;
  duration_ms?: number | null;
  error_message?: string | null;
  ran_at?: string | null;
};

export type AdminHealthResponse = {
  rows: HealthRow[];
};

export type AdminUser = {
  id: string;
  email: string;
  github_login?: string | null;
  plan?: string | null;
  is_admin?: boolean;
  is_agency?: boolean;
  created_at?: string | null;
};

export type AdminUsersResponse = {
  users: AdminUser[];
};

export const getAdminOverview = () => request<AdminOverview>("/admin/overview");

export const getPendingAlerts = () => request<PendingAlertsResponse>("/admin/alerts/pending");

export const approveAlert = (id: string) =>
  request<ApproveRejectResponse>(`/admin/alerts/${id}/approve`, { method: "POST" });

export const rejectAlert = (id: string) =>
  request<ApproveRejectResponse>(`/admin/alerts/${id}/reject`, { method: "POST" });

export const getAdminHealth = () => request<AdminHealthResponse>("/admin/health");

export const getAdminUsers = () => request<AdminUsersResponse>("/admin/users");
