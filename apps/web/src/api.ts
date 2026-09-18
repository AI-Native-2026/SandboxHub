import axios from "axios";
import { keycloak } from "./auth";

export const api = axios.create({ baseURL: "/api/v1" });

api.interceptors.request.use(async (cfg) => {
  if (keycloak.token) {
    try {
      await keycloak.updateToken(30);
    } catch {
      /* ignore */
    }
    cfg.headers.Authorization = `Bearer ${keycloak.token}`;
  }
  const tenant = localStorage.getItem("tenantId");
  if (tenant) cfg.headers["X-Tenant-Id"] = tenant;
  return cfg;
});

export interface TenantInfo {
  id: string;
  slug: string;
  name: string;
  role: string;
}

export interface Me {
  user: { id: string; username: string; email?: string; display_name?: string };
  roles: string[];
  is_platform_admin: boolean;
  tenants: TenantInfo[];
}

export async function getMe(): Promise<Me> {
  const { data } = await api.get("/me");
  return data;
}

export async function listSandboxes(params: Record<string, unknown> = {}) {
  const { data } = await api.get("/sandboxes", { params });
  return data;
}

export async function getSandbox(id: string) {
  const { data } = await api.get(`/sandboxes/${id}`);
  return data;
}

export async function createSandbox(body: Record<string, unknown>) {
  const { data } = await api.post("/sandboxes", body);
  return data;
}

export async function deleteSandbox(id: string) {
  await api.delete(`/sandboxes/${id}`);
}

export async function sandboxAction(id: string, action: string, body?: Record<string, unknown>) {
  const { data } = await api.post(`/sandboxes/${id}/${action}`, body || {});
  return data;
}

export async function getMetrics(id: string) {
  const { data } = await api.get(`/sandboxes/${id}/metrics`);
  return data;
}

export async function listFiles(id: string, path: string, depth = 1) {
  const { data } = await api.get(`/sandboxes/${id}/files/list`, { params: { path, depth } });
  return data.entries || [];
}

export async function writeFile(id: string, path: string, content: string) {
  const { data } = await api.post(`/sandboxes/${id}/files/write`, { path, content });
  return data;
}

export async function downloadFile(id: string, path: string): Promise<Blob> {
  const { data } = await api.get(`/sandboxes/${id}/files/download`, {
    params: { path },
    responseType: "blob",
  });
  return data;
}

export async function deleteFiles(id: string, paths: string[]) {
  const { data } = await api.delete(`/sandboxes/${id}/files`, { data: { paths } });
  return data;
}

export async function makeDirs(id: string, path: string) {
  const { data } = await api.post(`/sandboxes/${id}/directories`, { entries: [{ path, mode: 755 }] });
  return data;
}

export async function listTemplates() {
  const { data } = await api.get("/templates");
  return data;
}

export async function getOverview() {
  const { data } = await api.get("/overview");
  return data;
}

// ---- snapshots ----
export async function listSnapshots() {
  const { data } = await api.get("/snapshots");
  return data.items || [];
}
export async function createSnapshot(id: string, name: string) {
  const { data } = await api.post(`/sandboxes/${id}/snapshots`, { name });
  return data;
}
export async function deleteSnapshot(snapId: string) {
  await api.delete(`/snapshots/${snapId}`);
}

// ---- api keys ----
export async function listApiKeys() {
  const { data } = await api.get("/api-keys");
  return data;
}
export async function createApiKey(name: string, expiresInDays?: number | null) {
  const { data } = await api.post("/api-keys", { name, expires_in_days: expiresInDays || null });
  return data;
}
export async function revokeApiKey(id: string) {
  await api.delete(`/api-keys/${id}`);
}

// ---- templates (admin) ----
export async function createTemplate(body: any) {
  const { data } = await api.post("/templates", body);
  return data;
}
export async function updateTemplate(id: string, body: any) {
  const { data } = await api.put(`/templates/${id}`, body);
  return data;
}
export async function deleteTemplate(id: string) {
  await api.delete(`/templates/${id}`);
}

// ---- admin ----
export async function adminTenants() {
  const { data } = await api.get("/admin/tenants");
  return data;
}
export async function adminCreateTenant(body: any) {
  const { data } = await api.post("/admin/tenants", body);
  return data;
}
export async function adminPatchTenant(id: string, body: any) {
  const { data } = await api.patch(`/admin/tenants/${id}`, body);
  return data;
}
export async function adminMembers(id: string) {
  const { data } = await api.get(`/admin/tenants/${id}/members`);
  return data;
}
export async function adminAddMember(id: string, body: any) {
  const { data } = await api.post(`/admin/tenants/${id}/members`, body);
  return data;
}
export async function adminRemoveMember(id: string, userId: string) {
  await api.delete(`/admin/tenants/${id}/members/${userId}`);
}
export async function adminAudit(params: any = {}) {
  const { data } = await api.get("/admin/audit", { params });
  return data;
}
export async function adminMetrics() {
  const { data } = await api.get("/admin/metrics");
  return data;
}
export async function adminCleanup() {
  const { data } = await api.post("/admin/cleanup");
  return data;
}

// ---- U1 governance ----
export async function usageSummary(days = 7) {
  const { data } = await api.get("/usage/summary", { params: { days } });
  return data;
}
export async function usageTimeseries(days = 7) {
  const { data } = await api.get("/usage/timeseries", { params: { days } });
  return data;
}
export async function usageTop(days = 7) {
  const { data } = await api.get("/usage/top", { params: { days } });
  return data;
}
export async function getQuota() {
  const { data } = await api.get("/quota");
  return data;
}
export async function listApprovals(scope = "mine") {
  const { data } = await api.get("/approvals", { params: { scope } });
  return data;
}
export async function createApproval(body: any) {
  const { data } = await api.post("/approvals", body);
  return data;
}
export async function decideApproval(id: string, approve: boolean, note?: string) {
  const { data } = await api.post(`/approvals/${id}/decision`, { approve, note });
  return data;
}
export async function listCredentials() {
  const { data } = await api.get("/credentials");
  return data;
}
export async function createCredential(body: any) {
  const { data } = await api.post("/credentials", body);
  return data;
}
export async function deleteCredential(id: string) {
  await api.delete(`/credentials/${id}`);
}
export async function listPolicyTemplates() {
  const { data } = await api.get("/policy-templates");
  return data;
}
export async function createPolicyTemplate(body: any) {
  const { data } = await api.post("/policy-templates", body);
  return data;
}
export async function deletePolicyTemplate(id: string) {
  await api.delete(`/policy-templates/${id}`);
}

// ---- U3 security ----
export async function listRecordings() {
  const { data } = await api.get("/recordings");
  return data;
}
export async function getRecording(id: string) {
  const { data } = await api.get(`/recordings/${id}`);
  return data;
}
export async function deleteRecording(id: string) {
  await api.delete(`/recordings/${id}`);
}
export async function getRbac() {
  const { data } = await api.get("/rbac/roles");
  return data;
}
export async function createRole(body: any) {
  const { data } = await api.post("/rbac/roles", body);
  return data;
}
export async function deleteRole(id: string) {
  await api.delete(`/rbac/roles/${id}`);
}

// ---- U4 scale ----
export async function listPools() {
  const { data } = await api.get("/pools");
  return data;
}
export async function listPoolProviders() {
  const { data } = await api.get("/pools/providers");
  return data;
}
export async function createPool(body: any) {
  const { data } = await api.post("/pools", body);
  return data;
}
export async function deletePool(id: string) {
  await api.delete(`/pools/${id}`);
}
export async function observability(days = 7) {
  const { data } = await api.get("/observability", { params: { days } });
  return data;
}

// ---- U5 intelligence ----
export async function listTasks() {
  const { data } = await api.get("/tasks");
  return data;
}
export async function getTask(id: string) {
  const { data } = await api.get(`/tasks/${id}`);
  return data;
}
export async function createTask(body: any) {
  const { data } = await api.post("/tasks", body);
  return data;
}
export async function deleteTask(id: string) {
  await api.delete(`/tasks/${id}`);
}
export async function listArtifacts() {
  const { data } = await api.get("/artifacts");
  return data;
}
export async function collectArtifact(body: any) {
  const { data } = await api.post("/artifacts/collect", body);
  return data;
}
export async function deleteArtifact(id: string) {
  await api.delete(`/artifacts/${id}`);
}
export async function listAgents() {
  const { data } = await api.get("/agents");
  return data;
}
export async function launchAgent(id: string, body: Record<string, unknown> = {}) {
  const { data } = await api.post(`/agents/${id}/launch`, body);
  return data;
}


