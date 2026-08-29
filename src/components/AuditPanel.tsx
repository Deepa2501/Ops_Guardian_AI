import React from 'react';
import { Database, Lock, CheckCircle2, AlertTriangle, RefreshCw } from 'lucide-react';
import { AuditLog } from '../types';

interface AuditPanelProps {
  logs: AuditLog[];
  chainValid?: boolean | null;
  onVerify?: () => void;
  verifying?: boolean;
}

const STATUS_COLORS: Record<string, string> = {
  ALLOW: 'text-green-400',
  HOLD: 'text-yellow-400',
  BLOCK: 'text-red-400',
  RELEASED: 'text-blue-400',
  AUTHORIZED: 'text-green-400',
  OUT_OF_SCOPE: 'text-yellow-400',
  POLICY_BLOCKED: 'text-red-400',
  HUMAN_APPROVAL: 'text-blue-400',
  HUMAN_REJECTION: 'text-red-400',
};

/**
 * Audit trail panel with SHA-256 hash chain verification status.
 */
export function AuditPanel({ logs, chainValid, onVerify, verifying }: AuditPanelProps) {
  return (
    <div className="space-y-3">
      {/* Hash chain integrity */}
      <div className="flex items-center justify-between bg-gray-900/60 border border-gray-700 rounded-lg p-3">
        <div className="flex items-center gap-2">
          {chainValid === null || chainValid === undefined ? (
            <Database className="text-gray-500" size={14} />
          ) : chainValid ? (
            <CheckCircle2 className="text-green-400" size={14} />
          ) : (
            <AlertTriangle className="text-red-400" size={14} />
          )}
          <div>
            <p className="text-xs font-bold font-mono text-white">
              SHA-256 Hash Chain Integrity
            </p>
            <p className={`text-[10px] font-mono ${
              chainValid === null ? 'text-gray-500' :
              chainValid ? 'text-green-400' : 'text-red-400'
            }`}>
              {chainValid === null ? 'Not verified yet' :
               chainValid ? 'CHAIN INTACT — No tampering detected' :
               '⚠ CHAIN BROKEN — Audit tamper detected!'}
            </p>
          </div>
        </div>
        {onVerify && (
          <button
            onClick={onVerify}
            disabled={verifying}
            className="flex items-center gap-1 text-[10px] font-mono text-gray-400 hover:text-orange-300 border border-gray-700 hover:border-orange-500/40 rounded px-2 py-1 transition disabled:opacity-50"
          >
            <RefreshCw size={10} className={verifying ? 'animate-spin' : ''} />
            Verify
          </button>
        )}
      </div>

      {/* Audit log table */}
      <div className="overflow-x-auto">
        <table className="w-full text-[10px] font-mono border-collapse">
          <thead>
            <tr className="text-gray-600 border-b border-gray-800">
              <th className="text-left py-1.5 pr-3">Time</th>
              <th className="text-left py-1.5 pr-3">Task</th>
              <th className="text-left py-1.5 pr-3">Tool</th>
              <th className="text-left py-1.5 pr-3">ArmorIQ</th>
              <th className="text-left py-1.5 pr-3">Exec</th>
              <th className="text-left py-1.5">Event Hash</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id} className="border-b border-gray-800/50 hover:bg-gray-800/20 transition-colors">
                <td className="py-1.5 pr-3 text-gray-600 whitespace-nowrap">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </td>
                <td className="py-1.5 pr-3 text-gray-500 whitespace-nowrap">
                  {log.task_id?.slice(-8)}
                </td>
                <td className="py-1.5 pr-3 text-orange-300 whitespace-nowrap">
                  {log.tool_name}
                </td>
                <td className={`py-1.5 pr-3 font-bold whitespace-nowrap ${STATUS_COLORS[log.armoriq_status] ?? 'text-gray-400'}`}>
                  {log.armoriq_status}
                </td>
                <td className={`py-1.5 pr-3 whitespace-nowrap ${log.execution_status === 'EXECUTED' ? 'text-green-400' : log.execution_status === 'NOT_EXECUTED' ? 'text-gray-600' : 'text-red-400'}`}>
                  {log.execution_status}
                </td>
                <td className="py-1.5 text-gray-700 whitespace-nowrap">
                  {log.event_hash ? (
                    <span title={log.event_hash} className="cursor-help">
                      {log.event_hash.slice(0, 8)}...
                    </span>
                  ) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {logs.length === 0 && (
          <div className="text-center text-gray-600 py-8 font-mono text-xs">
            No audit events yet. Run the agent to populate audit trail.
          </div>
        )}
      </div>
    </div>
  );
}
