import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  ShieldAlert, ShieldCheck, Shield, Activity, AlertTriangle, CheckCircle2,
  XCircle, Clock, Play, RotateCcw, Cpu, Flame, Gauge, FileText, UserCheck,
  Lock, Layers, RefreshCw, Terminal, Database, Zap, Bell, ChevronDown, ChevronUp,
} from 'lucide-react';

import {
  AssetData, TelemetryPoint, WorkOrder, PendingApproval, AuditLog,
  Incident, AgentTask, RiskEvaluation, HealthStatus,
} from './types';
import { api } from './api';
import { AssetPanel } from './components/AssetPanel';
import { ApprovalCard } from './components/ApprovalCard';
import { AgentTimeline } from './components/AgentTimeline';
import { AuditPanel } from './components/AuditPanel';
import { SimulatorControls } from './components/SimulatorControls';

// ── Types ─────────────────────────────────────────────────────────────────────

type Tab = 'overview' | 'agent' | 'approvals' | 'incidents' | 'work-orders' | 'audit' | 'simulator';

// ── Main Application ──────────────────────────────────────────────────────────

export default function App() {
  // ── State ──────────────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  // Data
  const [assets, setAssets] = useState<AssetData[]>([]);
  const [telemetry, setTelemetry] = useState<TelemetryPoint[]>([]);
  const [risk, setRisk] = useState<RiskEvaluation | null>(null);
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [agentTasks, setAgentTasks] = useState<AgentTask[]>([]);
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);

  // UI State
  const [isAgentRunning, setIsAgentRunning] = useState(false);
  const [agentResult, setAgentResult] = useState<any>(null);
  const [processingApproval, setProcessingApproval] = useState<string | null>(null);
  const [isResetting, setIsResetting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [chainValid, setChainValid] = useState<boolean | null>(null);
  const [verifyingChain, setVerifyingChain] = useState(false);
  const [taskPrompt, setTaskPrompt] = useState(
    'Monitor Production Unit A, analyze reliability problems, and autonomously create preventive maintenance work orders.'
  );
  const [backendReady, setBackendReady] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  // Simulator
  const [activeScenario, setActiveScenario] = useState<string | null>(null);
  const [simulatorTicks, setSimulatorTicks] = useState(0);
  const refreshTimerRef = useRef<number | null>(null);

  // ── Data fetching ──────────────────────────────────────────────────────────

  const fetchAll = useCallback(async () => {
    try {
      const [assetsData, telData, woData, approvData, auditData, incData, tasksData, riskData] =
        await Promise.allSettled([
          api.getAssets(),
          api.getTelemetry('AST-01', 30),
          api.getWorkOrders(),
          api.getApprovals(),
          api.getAuditTrail(50),
          api.getIncidents(),
          api.getAgentTasks(),
          api.getAssetRisk('AST-01'),
        ]);

      if (assetsData.status === 'fulfilled') setAssets(assetsData.value);
      if (telData.status === 'fulfilled') setTelemetry(telData.value);
      if (woData.status === 'fulfilled') setWorkOrders(woData.value);
      if (approvData.status === 'fulfilled') setApprovals(approvData.value);
      if (auditData.status === 'fulfilled') setAuditLogs(auditData.value);
      if (incData.status === 'fulfilled') setIncidents(incData.value);
      if (tasksData.status === 'fulfilled') setAgentTasks(tasksData.value);
      if (riskData.status === 'fulfilled') setRisk(riskData.value);
    } catch {
      // silently ignore during startup
    }
  }, []);

  const checkHealth = useCallback(async () => {
    try {
      const h = await api.getHealth();
      setHealthStatus(h);
      setBackendReady(true);
      return true;
    } catch {
      return false;
    }
  }, []);

  // Initial load + polling
  useEffect(() => {
    let retries = 0;
    const pollHealth = async () => {
      const ok = await checkHealth();
      if (ok) {
        await fetchAll();
        setLoading(false);
      } else {
        retries++;
        setStatusMsg(`Connecting to backend... (attempt ${retries})`);
        if (retries < 30) setTimeout(pollHealth, 2000);
      }
    };
    pollHealth();
  }, [checkHealth, fetchAll]);

  // Auto-refresh every 15s
  useEffect(() => {
    if (!backendReady) return;
    refreshTimerRef.current = window.setInterval(() => {
      fetchAll();
      if (activeScenario) {
        api.getSimulatorStatus().then((s) => {
          const sc = s.active_scenarios?.['AST-01'];
          if (sc) setSimulatorTicks(sc.ticks);
        }).catch(() => {});
      }
    }, 15000);
    return () => { if (refreshTimerRef.current) clearInterval(refreshTimerRef.current); };
  }, [backendReady, fetchAll, activeScenario]);

  // ── Handlers ───────────────────────────────────────────────────────────────

  const handleRunAgent = async () => {
    setIsAgentRunning(true);
    setAgentResult(null);
    setActiveTab('agent');
    try {
      const result = await api.runAgent(taskPrompt, 'AST-01');
      setAgentResult(result);
      await fetchAll();
    } catch (e: any) {
      setAgentResult({ error: e.message });
    } finally {
      setIsAgentRunning(false);
    }
  };

  const handleApprove = async (actionId: string, reviewer: string, notes: string) => {
    setProcessingApproval(actionId);
    try {
      await api.approveAction(actionId, reviewer, notes);
      await fetchAll();
    } catch (e: any) {
      alert(`Approval failed: ${e.message}`);
    } finally {
      setProcessingApproval(null);
    }
  };

  const handleReject = async (actionId: string, reviewer: string, reason: string) => {
    setProcessingApproval(actionId);
    try {
      await api.rejectAction(actionId, reviewer, reason);
      await fetchAll();
    } catch (e: any) {
      alert(`Rejection failed: ${e.message}`);
    } finally {
      setProcessingApproval(null);
    }
  };

  const handleReset = async () => {
    setIsResetting(true);
    try {
      await api.resetDemo();
      setAgentResult(null);
      setActiveScenario(null);
      setSimulatorTicks(0);
      await fetchAll();
    } finally {
      setIsResetting(false);
    }
  };

  const handleVerifyChain = async () => {
    setVerifyingChain(true);
    try {
      const result = await api.verifyAuditChain();
      setChainValid(result.valid);
    } finally {
      setVerifyingChain(false);
    }
  };

  const handleSetScenario = async (scenario: string) => {
    try {
      await api.setScenario('AST-01', scenario);
      setActiveScenario(scenario);
      setSimulatorTicks(1);
      await fetchAll();
    } catch (e: any) {
      alert(`Scenario failed: ${e.message}`);
    }
  };

  const handleAdvanceTick = async () => {
    if (!activeScenario) return;
    try {
      await api.advanceTick('AST-01', activeScenario);
      setSimulatorTicks((t) => t + 1);
      await fetchAll();
    } catch (e: any) {
      alert(`Tick failed: ${e.message}`);
    }
  };

  const handleStopSimulator = async () => {
    try {
      await api.stopSimulator();
      setActiveScenario(null);
      setSimulatorTicks(0);
    } catch {}
  };

  // ── Counts ─────────────────────────────────────────────────────────────────

  const pendingApprovalCount = approvals.filter((a) => a.status === 'PENDING_APPROVAL').length;
  const openIncidentCount = incidents.filter((i) => !['RESOLVED', 'CLOSED'].includes(i.status)).length;
  const asset = assets[0] ?? null;
  const govMode = healthStatus?.components?.governance_mode ?? 'mock';

  // ── Loading screen ─────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <div className="text-orange-400 text-2xl font-bold font-mono mb-2">OPSGuardian AI</div>
          <div className="text-gray-400 text-sm font-mono mb-6">+ ArmorIQ Governance Platform</div>
          <div className="flex items-center gap-2 text-gray-500 text-sm font-mono">
            <RefreshCw className="animate-spin" size={16} />
            {statusMsg || 'Initializing...'}
          </div>
        </div>
      </div>
    );
  }

  // ── Main UI ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 font-sans">
      {/* Top bar */}
      <header className="border-b border-gray-800 bg-gray-950/95 sticky top-0 z-30 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <div className="relative">
              <Shield className="text-orange-400" size={24} />
              {pendingApprovalCount > 0 && (
                <span className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-red-500 rounded-full flex items-center justify-center text-[8px] font-bold text-white">
                  {pendingApprovalCount}
                </span>
              )}
            </div>
            <div>
              <div className="text-white font-bold text-sm font-mono tracking-tight">OPSGuardian AI</div>
              <div className="text-[10px] text-gray-600 font-mono">+ ArmorIQ Governance v2.0</div>
            </div>
          </div>

          {/* Status pills */}
          <div className="flex items-center gap-2 flex-1 justify-center flex-wrap">
            <StatusPill
              label={`ArmorIQ: ${govMode.toUpperCase()}`}
              active={govMode !== 'disabled'}
              icon={<Shield size={9} />}
            />
            <StatusPill
              label={`AI: ${healthStatus?.components?.ai_provider ?? 'deterministic'}`}
              active
              icon={<Cpu size={9} />}
            />
            {asset && risk && (
              <StatusPill
                label={`Risk: ${risk.risk_level} (${risk.risk_score.toFixed(0)})`}
                active={risk.risk_level !== 'LOW'}
                variant={risk.risk_level === 'CRITICAL' ? 'danger' : risk.risk_level === 'HIGH' ? 'warn' : 'ok'}
                icon={<Activity size={9} />}
              />
            )}
            {pendingApprovalCount > 0 && (
              <StatusPill
                label={`${pendingApprovalCount} Pending Approval${pendingApprovalCount > 1 ? 's' : ''}`}
                active
                variant="warn"
                icon={<ShieldAlert size={9} />}
              />
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchAll()}
              className="p-1.5 text-gray-600 hover:text-gray-400 transition"
              title="Refresh"
            >
              <RefreshCw size={14} />
            </button>
            <button
              onClick={handleReset}
              disabled={isResetting}
              className="flex items-center gap-1.5 text-xs font-mono text-gray-500 hover:text-orange-400 border border-gray-700 hover:border-orange-500/40 rounded px-2.5 py-1 transition disabled:opacity-50"
            >
              <RotateCcw size={12} className={isResetting ? 'animate-spin' : ''} />
              Reset Demo
            </button>
          </div>
        </div>

        {/* Navigation tabs */}
        <div className="max-w-7xl mx-auto px-4 pb-0 flex gap-1 overflow-x-auto">
          {(
            [
              { id: 'overview' as Tab, label: 'Overview', icon: <Layers size={12} /> },
              { id: 'agent' as Tab, label: 'Agent', icon: <Terminal size={12} /> },
              { id: 'approvals' as Tab, label: `Approvals${pendingApprovalCount > 0 ? ` (${pendingApprovalCount})` : ''}`, icon: <ShieldAlert size={12} /> },
              { id: 'incidents' as Tab, label: `Incidents${openIncidentCount > 0 ? ` (${openIncidentCount})` : ''}`, icon: <AlertTriangle size={12} /> },
              { id: 'work-orders' as Tab, label: `Work Orders${workOrders.length > 0 ? ` (${workOrders.length})` : ''}`, icon: <FileText size={12} /> },
              { id: 'audit' as Tab, label: 'Audit', icon: <Database size={12} /> },
              { id: 'simulator' as Tab, label: `Simulator${activeScenario ? ' ●' : ''}`, icon: <Zap size={12} /> },
            ] as const
          ).map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`flex items-center gap-1.5 px-3 py-2 text-[11px] font-mono whitespace-nowrap border-b-2 transition-colors ${
                activeTab === t.id
                  ? 'border-orange-500 text-orange-400'
                  : 'border-transparent text-gray-500 hover:text-gray-300'
              }`}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-6">

        {/* ── OVERVIEW TAB ─────────────────────────────────────────────────── */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Asset Panel */}
            {asset ? (
              <AssetPanel
                asset={asset}
                telemetry={telemetry}
                risk={risk ?? undefined}
                productionConfig={assets.length > 0 ? { load_percent: asset.load_percent, safety_interlock: 'NORMAL' } : undefined}
              />
            ) : (
              <div className="text-center text-gray-600 py-12 font-mono text-sm">
                No assets found. Backend may still be loading.
              </div>
            )}

            {/* Open Incidents */}
            {incidents.filter((i) => !['RESOLVED', 'CLOSED'].includes(i.status)).length > 0 && (
              <div>
                <SectionHeader title="Active Incidents" icon={<AlertTriangle size={14} />} count={openIncidentCount} />
                <div className="space-y-2 mt-3">
                  {incidents
                    .filter((i) => !['RESOLVED', 'CLOSED'].includes(i.status))
                    .slice(0, 3)
                    .map((inc) => (
                      <IncidentRow key={inc.id} incident={inc} />
                    ))}
                </div>
              </div>
            )}

            {/* Recent Work Orders */}
            {workOrders.length > 0 && (
              <div>
                <SectionHeader title="Recent Work Orders" icon={<FileText size={14} />} count={workOrders.length} />
                <div className="space-y-2 mt-3">
                  {workOrders.slice(0, 4).map((wo) => (
                    <WorkOrderRow key={wo.id} wo={wo} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── AGENT TAB ────────────────────────────────────────────────────── */}
        {activeTab === 'agent' && (
          <div className="space-y-4">
            {/* Run agent card */}
            <div className="bg-gray-900/60 border border-gray-700 rounded-xl p-5">
              <div className="flex items-start gap-3 mb-4">
                <Terminal className="text-orange-400 shrink-0 mt-0.5" size={18} />
                <div className="flex-1">
                  <p className="text-white font-bold text-sm font-mono">Autonomous Operations Agent</p>
                  <p className="text-gray-500 text-[11px]">
                    Governed by ArmorIQ. Mode:{' '}
                    <span className="text-orange-400 font-mono">{govMode.toUpperCase()}</span>.
                    AI:{' '}
                    <span className="text-orange-400 font-mono">
                      {healthStatus?.components?.ai_provider ?? 'deterministic'}
                    </span>
                  </p>
                </div>
              </div>
              <textarea
                value={taskPrompt}
                onChange={(e) => setTaskPrompt(e.target.value)}
                rows={2}
                className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm font-mono text-white resize-none focus:outline-none focus:border-orange-500 mb-3"
              />
              <button
                onClick={handleRunAgent}
                disabled={isAgentRunning}
                className="w-full flex items-center justify-center gap-2 bg-orange-600/80 hover:bg-orange-600 border border-orange-500/60 text-white rounded-lg px-4 py-2.5 text-sm font-bold font-mono transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isAgentRunning ? (
                  <>
                    <RefreshCw size={14} className="animate-spin" />
                    Agent Running...
                  </>
                ) : (
                  <>
                    <Play size={14} />
                    Deploy Autonomous Agent
                  </>
                )}
              </button>
            </div>

            {/* Agent result */}
            {agentResult && (
              <div className="bg-gray-900/60 border border-gray-700 rounded-xl p-5 space-y-4">
                {agentResult.error ? (
                  <div className="text-red-400 font-mono text-sm">{agentResult.error}</div>
                ) : (
                  <>
                    <div className="flex items-center justify-between">
                      <p className="text-white font-bold text-sm font-mono">Execution Report</p>
                      <span className={`text-[10px] font-bold font-mono border rounded px-2 py-0.5 ${
                        agentResult.status === 'HELD_PENDING_APPROVAL'
                          ? 'text-yellow-400 border-yellow-500/40 bg-yellow-900/10'
                          : 'text-green-400 border-green-500/40 bg-green-900/10'
                      }`}>
                        {agentResult.status}
                      </span>
                    </div>

                    {/* Governance badge */}
                    <div className="bg-gray-900/60 border border-gray-700 rounded p-3 text-[11px] font-mono grid grid-cols-2 gap-2">
                      <div><span className="text-gray-500">Task ID:</span> <span className="text-orange-300">{agentResult.task_id}</span></div>
                      <div><span className="text-gray-500">Plan ID:</span> <span className="text-orange-300">{agentResult.plan_id?.slice(0, 20)}...</span></div>
                      <div><span className="text-gray-500">AI Provider:</span> <span className="text-blue-300">{agentResult.diagnosis_provider ?? '—'}</span></div>
                      <div><span className="text-gray-500">Fallback:</span> <span className={agentResult.fallback_used ? 'text-yellow-400' : 'text-green-400'}>{agentResult.fallback_used ? 'YES' : 'NO'}</span></div>
                    </div>

                    {/* Timeline */}
                    {agentResult.execution_steps && (
                      <AgentTimeline
                        steps={agentResult.execution_steps}
                        taskId={agentResult.task_id}
                        planId={agentResult.plan_id}
                        planHash={agentResult.plan_hash}
                        status={agentResult.status}
                      />
                    )}
                  </>
                )}
              </div>
            )}

            {/* Recent tasks */}
            {agentTasks.length > 0 && (
              <div>
                <SectionHeader title="Agent Task History" icon={<Clock size={14} />} count={agentTasks.length} />
                <div className="space-y-2 mt-3">
                  {agentTasks.slice(0, 5).map((t) => (
                    <TaskRow key={t.id} task={t} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── APPROVALS TAB ────────────────────────────────────────────────── */}
        {activeTab === 'approvals' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <SectionHeader title="ArmorIQ Approval Queue" icon={<ShieldAlert size={14} />} count={approvals.length} />
              <button onClick={() => fetchAll()} className="text-[10px] font-mono text-gray-500 hover:text-gray-300 flex items-center gap-1">
                <RefreshCw size={10} /> Refresh
              </button>
            </div>

            {approvals.length === 0 ? (
              <div className="text-center text-gray-600 py-12 font-mono text-sm border border-gray-800 rounded-xl">
                No pending approvals. Run the agent to generate a governance hold.
              </div>
            ) : (
              <div className="space-y-4">
                {approvals.map((a) => (
                  <ApprovalCard
                    key={a.action_id}
                    approval={a}
                    onApprove={handleApprove}
                    onReject={handleReject}
                    isProcessing={processingApproval === a.action_id}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── INCIDENTS TAB ────────────────────────────────────────────────── */}
        {activeTab === 'incidents' && (
          <div className="space-y-3">
            <SectionHeader title="Incident Register" icon={<AlertTriangle size={14} />} count={incidents.length} />
            {incidents.length === 0 ? (
              <div className="text-center text-gray-600 py-12 font-mono text-sm border border-gray-800 rounded-xl">
                No incidents recorded.
              </div>
            ) : (
              incidents.map((inc) => (
                <IncidentCard
                  key={inc.id}
                  incident={inc}
                  onAcknowledge={async (id) => { await api.acknowledgeIncident(id); await fetchAll(); }}
                  onResolve={async (id) => { await api.resolveIncident(id); await fetchAll(); }}
                />
              ))
            )}
          </div>
        )}

        {/* ── WORK ORDERS TAB ──────────────────────────────────────────────── */}
        {activeTab === 'work-orders' && (
          <div className="space-y-3">
            <SectionHeader title="Work Order Register" icon={<FileText size={14} />} count={workOrders.length} />
            {workOrders.length === 0 ? (
              <div className="text-center text-gray-600 py-12 font-mono text-sm border border-gray-800 rounded-xl">
                No work orders. Run the agent to auto-generate a P1 work order.
              </div>
            ) : (
              workOrders.map((wo) => <WorkOrderCard key={wo.id} wo={wo} />)
            )}
          </div>
        )}

        {/* ── AUDIT TAB ────────────────────────────────────────────────────── */}
        {activeTab === 'audit' && (
          <div className="space-y-4">
            <SectionHeader title="Cryptographic Audit Trail" icon={<Database size={14} />} count={auditLogs.length} />
            <AuditPanel
              logs={auditLogs}
              chainValid={chainValid}
              onVerify={handleVerifyChain}
              verifying={verifyingChain}
            />
          </div>
        )}

        {/* ── SIMULATOR TAB ────────────────────────────────────────────────── */}
        {activeTab === 'simulator' && (
          <div className="space-y-4">
            <SimulatorControls
              activeScenario={activeScenario}
              onSetScenario={handleSetScenario}
              onStop={handleStopSimulator}
              onAdvanceTick={handleAdvanceTick}
              ticks={simulatorTicks}
            />
            {activeScenario && asset && (
              <AssetPanel
                asset={asset}
                telemetry={telemetry}
                risk={risk ?? undefined}
              />
            )}
          </div>
        )}
      </main>
    </div>
  );
}

// ── Reusable sub-components ───────────────────────────────────────────────────

function StatusPill({
  label, active, icon, variant = 'ok',
}: { label: string; active: boolean; icon?: React.ReactNode; variant?: 'ok' | 'warn' | 'danger' }) {
  const colors = {
    ok: active ? 'text-green-400 border-green-500/30 bg-green-500/10' : 'text-gray-600 border-gray-700 bg-gray-800/50',
    warn: 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10',
    danger: 'text-red-400 border-red-500/30 bg-red-500/10 animate-pulse',
  };
  return (
    <div className={`flex items-center gap-1 border rounded px-2 py-0.5 text-[10px] font-mono ${colors[variant]}`}>
      {icon}
      {label}
    </div>
  );
}

function SectionHeader({ title, icon, count }: { title: string; icon: React.ReactNode; count?: number }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-orange-400">{icon}</span>
      <h2 className="text-white font-bold text-sm font-mono">{title}</h2>
      {count !== undefined && (
        <span className="text-[10px] text-gray-600 font-mono bg-gray-800 border border-gray-700 rounded px-1.5 py-0.5">
          {count}
        </span>
      )}
    </div>
  );
}

function IncidentRow({ incident }: { incident: Incident }) {
  const sev = {
    CRITICAL: 'text-red-400',
    HIGH: 'text-orange-400',
    MEDIUM: 'text-yellow-400',
    LOW: 'text-green-400',
  }[incident.severity] ?? 'text-gray-400';
  return (
    <div className="flex items-center gap-3 bg-gray-900/40 border border-gray-700 rounded-lg px-3 py-2">
      <AlertTriangle className={sev} size={13} />
      <div className="flex-1 min-w-0">
        <p className="text-white text-xs font-semibold truncate">{incident.title}</p>
        <p className="text-gray-500 text-[10px] font-mono">{incident.id} · {incident.status}</p>
      </div>
      <span className={`text-[10px] font-bold font-mono ${sev}`}>{incident.severity}</span>
    </div>
  );
}

function WorkOrderRow({ wo }: { wo: WorkOrder }) {
  const pcolor = { P1: 'text-red-400', P2: 'text-orange-400', P3: 'text-yellow-400', P4: 'text-green-400' }[wo.priority] ?? 'text-gray-400';
  return (
    <div className="flex items-center gap-3 bg-gray-900/40 border border-gray-700 rounded-lg px-3 py-2">
      <FileText className="text-gray-500" size={13} />
      <div className="flex-1 min-w-0">
        <p className="text-white text-xs font-semibold truncate">{wo.title}</p>
        <p className="text-gray-500 text-[10px] font-mono">{wo.id} · {wo.assigned_to}</p>
      </div>
      <span className={`text-[10px] font-bold font-mono ${pcolor}`}>{wo.priority}</span>
    </div>
  );
}

function IncidentCard({
  incident, onAcknowledge, onResolve,
}: { incident: Incident; onAcknowledge: (id: string) => void; onResolve: (id: string) => void }) {
  const sev = { CRITICAL: 'border-red-500/40 bg-red-900/10', HIGH: 'border-orange-500/40 bg-orange-900/10', MEDIUM: 'border-yellow-500/40 bg-yellow-900/10', LOW: 'border-gray-700 bg-gray-900/20' }[incident.severity] ?? 'border-gray-700 bg-gray-900/20';
  return (
    <div className={`border rounded-xl p-4 space-y-2 ${sev}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-white font-bold text-sm">{incident.title}</p>
          <p className="text-gray-500 text-[10px] font-mono">{incident.id} · {incident.asset_id} · {incident.failure_mode}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className="text-[10px] font-bold font-mono text-orange-400">{incident.severity}</span>
          <span className="text-[10px] text-gray-500 font-mono">{incident.status}</span>
        </div>
      </div>
      {incident.details && <p className="text-gray-400 text-[11px]">{incident.details}</p>}
      {incident.risk_score !== undefined && (
        <p className="text-[10px] text-gray-500 font-mono">Risk Score: <span className="text-orange-400 font-bold">{incident.risk_score.toFixed(0)}/100</span></p>
      )}
      {incident.status === 'DETECTED' && (
        <button onClick={() => onAcknowledge(incident.id)} className="text-[10px] font-mono text-blue-400 hover:text-blue-300 border border-blue-500/30 rounded px-2 py-0.5 transition">
          Acknowledge
        </button>
      )}
      {incident.status === 'INVESTIGATING' && (
        <button onClick={() => onResolve(incident.id)} className="text-[10px] font-mono text-green-400 hover:text-green-300 border border-green-500/30 rounded px-2 py-0.5 transition">
          Mark Resolved
        </button>
      )}
    </div>
  );
}

function WorkOrderCard({ wo }: { wo: WorkOrder }) {
  const pcolor = { P1: 'text-red-400 border-red-500/40', P2: 'text-orange-400 border-orange-500/40', P3: 'text-yellow-400 border-yellow-500/40', P4: 'text-green-400 border-green-500/40' }[wo.priority] ?? 'text-gray-400 border-gray-700';
  return (
    <div className="border border-gray-700 bg-gray-900/40 rounded-xl p-4 space-y-1.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-bold font-mono border rounded px-1.5 py-0.5 ${pcolor}`}>{wo.priority}</span>
          <p className="text-white font-semibold text-sm">{wo.title}</p>
        </div>
        <span className="text-[10px] text-gray-500 font-mono">{wo.status}</span>
      </div>
      <p className="text-gray-400 text-[11px]">{wo.description}</p>
      <p className="text-gray-600 text-[10px] font-mono">
        {wo.id} · Assigned: {wo.assigned_to} · {wo.created_at ? new Date(wo.created_at).toLocaleDateString() : ''}
      </p>
    </div>
  );
}

function TaskRow({ task }: { task: AgentTask }) {
  const statusColor = {
    COMPLETED: 'text-green-400',
    HELD_PENDING_APPROVAL: 'text-yellow-400',
    RUNNING: 'text-blue-400',
    FAILED: 'text-red-400',
    CANCELLED: 'text-gray-600',
  }[task.status] ?? 'text-gray-400';
  return (
    <div className="flex items-center gap-3 bg-gray-900/40 border border-gray-700 rounded-lg px-3 py-2">
      <Terminal className="text-gray-500 shrink-0" size={13} />
      <div className="flex-1 min-w-0">
        <p className="text-white text-xs font-semibold truncate">{task.goal.slice(0, 60)}...</p>
        <p className="text-gray-500 text-[10px] font-mono">{task.id}</p>
      </div>
      <span className={`text-[10px] font-bold font-mono shrink-0 ${statusColor}`}>{task.status}</span>
    </div>
  );
}
