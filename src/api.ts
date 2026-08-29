/* OPSGuardian AI + ArmorIQ — Centralized API client */

const API_BASE = '/api';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  // Health
  getHealth: () => apiFetch<any>('/health'),
  getAIHealth: () => apiFetch<any>('/health/ai'),
  getGovernanceHealth: () => apiFetch<any>('/health/governance'),
  getDBHealth: () => apiFetch<any>('/health/database'),

  // Assets & Telemetry
  getAssets: () => apiFetch<any[]>('/assets'),
  getTelemetry: (assetId: string, limit = 30) =>
    apiFetch<any[]>(`/telemetry/${assetId}?limit=${limit}`),

  // Risk
  getAssetRisk: (assetId: string) => apiFetch<any>(`/risk/${assetId}`),

  // Incidents
  getIncidents: () => apiFetch<any[]>('/incidents'),
  acknowledgeIncident: (id: string) =>
    apiFetch<any>(`/incidents/${id}/acknowledge`, { method: 'POST' }),
  resolveIncident: (id: string) =>
    apiFetch<any>(`/incidents/${id}/resolve`, { method: 'POST' }),

  // Work Orders
  getWorkOrders: () => apiFetch<any[]>('/work-orders'),

  // Production Config
  getProductionConfig: (assetId: string) =>
    apiFetch<any>(`/production-config/${assetId}`),

  // Agent
  runAgent: (task: string, assetId = 'AST-01') =>
    apiFetch<any>('/agent/run', {
      method: 'POST',
      body: JSON.stringify({ task, asset_id: assetId, allow_gemini: true }),
    }),
  getAgentTasks: () => apiFetch<any[]>('/agent/tasks'),
  getAgentTask: (id: string) => apiFetch<any>(`/agent/tasks/${id}`),
  cancelAgentTask: (id: string) =>
    apiFetch<any>(`/agent/tasks/${id}/cancel`, { method: 'POST' }),

  // Approvals
  getApprovals: (status?: string) =>
    apiFetch<any[]>(`/approvals${status ? `?status=${status}` : ''}`),
  approveAction: (actionId: string, reviewer: string, notes: string) =>
    apiFetch<any>(`/approvals/${actionId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ action_id: actionId, reviewer, notes }),
    }),
  rejectAction: (actionId: string, reviewer: string, reason: string) =>
    apiFetch<any>(`/approvals/${actionId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ action_id: actionId, reviewer, reason }),
    }),

  // Audit
  getAuditTrail: (limit = 50) => apiFetch<any[]>(`/audit?limit=${limit}`),
  verifyAuditChain: () => apiFetch<any>('/audit/verify'),

  // Simulator
  setScenario: (assetId: string, scenario: string) =>
    apiFetch<any>('/simulator/scenario', {
      method: 'POST',
      body: JSON.stringify({ asset_id: assetId, scenario }),
    }),
  advanceTick: (assetId: string, scenario: string) =>
    apiFetch<any>('/simulator/tick', {
      method: 'POST',
      body: JSON.stringify({ asset_id: assetId, scenario }),
    }),
  stopSimulator: () =>
    apiFetch<any>('/simulator/stop', { method: 'POST' }),
  getSimulatorStatus: () => apiFetch<any>('/simulator/status'),

  // Demo
  resetDemo: () => apiFetch<any>('/demo/reset', { method: 'POST' }),
};
