/* OPSGuardian AI + ArmorIQ — Core TypeScript types */

export interface AssetData {
  id: string;
  name: string;
  type: string;
  location: string;
  critical_level: string;
  status: string;
  health_score: number;
  load_percent: number;
  vibration_mms: number;
  temperature_c: number;
  pressure_bar: number;
}

export interface TelemetryPoint {
  id: number;
  timestamp: string;
  vibration_mms: number;
  temperature_c: number;
  pressure_bar: number;
  rpm: number;
  load_percent: number;
  anomaly_flag: boolean;
  summary: string;
}

export interface WorkOrder {
  id: string;
  asset_id: string;
  title: string;
  description: string;
  priority: string;
  assigned_to: string;
  status: string;
  plan_id?: string;
  created_at: string;
}

export interface PendingApproval {
  action_id: string;
  task_id: string;
  plan_id: string;
  tool_name: string;
  arguments: Record<string, any>;
  delegation_id: string;
  status: string;
  armoriq_status: string;
  reason: string;
  created_at: string;
  reviewed_by?: string;
  reviewed_at?: string;
  review_notes?: string;
}

export interface AuditLog {
  id: number;
  timestamp: string;
  task_id: string;
  plan_id: string;
  action_id: string;
  agent_id: string;
  tool_name: string;
  arguments: Record<string, any>;
  authorization_status: string;
  armoriq_status: string;
  execution_status: string;
  hold_reason?: string;
  human_approval: string;
  final_result?: string;
  event_hash?: string;
  previous_event_hash?: string;
  arguments_hash?: string;
}

export interface Incident {
  id: string;
  asset_id: string;
  title: string;
  severity: string;
  failure_mode: string;
  details?: string;
  description?: string;
  risk_score?: number;
  status: string;
  detected_at?: string;
  acknowledged_at?: string;
  resolved_at?: string;
  created_at: string;
  created_by_task_id?: string;
}

export interface AgentTask {
  id: string;
  goal: string;
  asset_id?: string;
  status: string;
  plan_id?: string;
  plan_hash?: string;
  steps_count: number;
  current_step: number;
  summary?: string;
  risk_score?: number;
  risk_level?: string;
  requires_approval: boolean;
  approval_action_id?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface ThreatVector {
  score: number;
  factors: string[];
  iso_10816_zone?: string;
  vibration_mms?: number;
  temperature_c?: number;
  pressure_bar?: number;
  load_percent?: number;
}

export interface RiskEvaluation {
  risk_score: number;
  risk_level: string;
  threat_vectors: {
    mechanical: ThreatVector;
    thermal: ThreatVector;
    lubrication: ThreatVector;
    production_stress: ThreatVector;
    sensor_anomaly: ThreatVector;
  };
  risk_factors: string[];
  recommended_action: string;
  confidence: number;
  failure_probability_24h: number;
  iso_10816_zone: string;
}

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  components: {
    database: string;
    ai: string;
    ai_provider: string;
    governance: string;
    governance_mode: string;
  };
  timestamp: string;
}

export interface SimulatorStatus {
  running: boolean;
  active_scenarios: Record<string, { scenario: string; ticks: number }>;
  available_scenarios: string[];
}
