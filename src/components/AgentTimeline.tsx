import React from 'react';
import { Terminal, ChevronRight, ShieldAlert, ShieldCheck, Shield } from 'lucide-react';

interface AgentStep {
  step_number: number;
  label: string;
  action: string;
  armoriq_status: string;
  execution: string;
  details?: any;
}

interface AgentTimelineProps {
  steps: AgentStep[];
  taskId: string;
  planId?: string;
  planHash?: string;
  status: string;
}

/**
 * Timeline visualization of agent execution steps with ArmorIQ decision badges.
 */
export function AgentTimeline({ steps, taskId, planId, planHash, status }: AgentTimelineProps) {
  const [expanded, setExpanded] = React.useState<number | null>(null);

  const statusMap: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
    ALLOW: { color: 'text-green-400', icon: <ShieldCheck size={12} />, label: 'ALLOW' },
    HOLD: { color: 'text-yellow-400', icon: <ShieldAlert size={12} />, label: 'HOLD' },
    BLOCK: { color: 'text-red-400', icon: <Shield size={12} />, label: 'BLOCK' },
  };

  const execMap: Record<string, string> = {
    EXECUTED: 'text-green-400',
    NOT_EXECUTED: 'text-gray-500',
    FAILED: 'text-red-400',
    CANCELLED: 'text-gray-600',
  };

  return (
    <div className="space-y-3">
      {/* Plan metadata */}
      {planId && (
        <div className="text-[10px] font-mono text-gray-600 border border-gray-800 bg-gray-900/40 rounded p-2">
          <span className="text-gray-500">PLAN</span>{' '}
          <span className="text-orange-400">{planId}</span>
          {planHash && (
            <span className="ml-2 text-gray-600">
              SHA256: {planHash.slice(0, 16)}...
            </span>
          )}
        </div>
      )}

      {/* Steps */}
      <div className="space-y-2">
        {steps.map((step) => {
          const armoriqStatus = statusMap[step.armoriq_status] ?? statusMap['BLOCK'];
          const isHeld = step.armoriq_status === 'HOLD';
          const isExpanded = expanded === step.step_number;

          return (
            <div
              key={step.step_number}
              className={`rounded-lg border transition-all ${
                isHeld
                  ? 'border-yellow-500/40 bg-yellow-900/10'
                  : 'border-gray-700 bg-gray-900/30'
              }`}
            >
              <button
                className="w-full flex items-center gap-3 p-3 text-left"
                onClick={() => setExpanded(isExpanded ? null : step.step_number)}
              >
                {/* Step number */}
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold font-mono shrink-0 ${
                  isHeld ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/40' :
                  step.execution === 'EXECUTED' ? 'bg-green-500/20 text-green-400 border border-green-500/40' :
                  'bg-gray-700 text-gray-500'
                }`}>
                  {step.step_number}
                </div>

                {/* Label + action */}
                <div className="flex-1 min-w-0">
                  <p className="text-white text-xs font-semibold truncate">{step.label}</p>
                  <p className="text-gray-500 text-[10px] font-mono truncate">{step.action}</p>
                </div>

                {/* ArmorIQ badge */}
                <div className={`flex items-center gap-1 text-[10px] font-bold font-mono border rounded px-1.5 py-0.5 shrink-0 ${
                  isHeld ? 'border-yellow-500/40 text-yellow-400' :
                  step.armoriq_status === 'ALLOW' ? 'border-green-500/40 text-green-400' :
                  'border-red-500/40 text-red-400'
                }`}>
                  {armoriqStatus.icon}
                  {armoriqStatus.label}
                </div>

                {/* Execution status */}
                <div className={`text-[10px] font-mono shrink-0 ${execMap[step.execution] ?? 'text-gray-500'}`}>
                  {step.execution === 'EXECUTED' ? '✓ RAN' : step.execution === 'NOT_EXECUTED' ? '○ HELD' : step.execution}
                </div>

                <ChevronRight
                  size={12}
                  className={`text-gray-600 shrink-0 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                />
              </button>

              {/* Expanded details */}
              {isExpanded && step.details && (
                <div className="border-t border-gray-700 px-3 pb-3">
                  <pre className="text-[10px] text-gray-400 font-mono overflow-auto max-h-48 mt-2 bg-gray-900/60 rounded p-2">
                    {JSON.stringify(step.details, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Overall status */}
      <div className={`text-center text-[11px] font-bold font-mono py-1 rounded border ${
        status === 'HELD_PENDING_APPROVAL'
          ? 'text-yellow-400 border-yellow-500/40 bg-yellow-900/10'
          : status === 'COMPLETED'
          ? 'text-green-400 border-green-500/40 bg-green-900/10'
          : status === 'FAILED'
          ? 'text-red-400 border-red-500/40 bg-red-900/10'
          : 'text-gray-400 border-gray-700'
      }`}>
        TASK STATUS: {status}
      </div>
    </div>
  );
}
