import React from 'react';
import { ShieldAlert, ShieldCheck, Shield, Clock, AlertTriangle } from 'lucide-react';
import { PendingApproval } from '../types';

interface ApprovalCardProps {
  approval: PendingApproval;
  onApprove: (actionId: string, reviewer: string, notes: string) => void;
  onReject: (actionId: string, reviewer: string, reason: string) => void;
  isProcessing?: boolean;
}

/**
 * Card displaying a single ArmorIQ HOLD action requiring human supervisor approval.
 * Shows tool name, arguments, reason, delegation ID, and approve/reject controls.
 */
export function ApprovalCard({
  approval,
  onApprove,
  onReject,
  isProcessing = false,
}: ApprovalCardProps) {
  const [reviewer, setReviewer] = React.useState('lead_operations_engineer@opsguardian.ai');
  const [notes, setNotes] = React.useState('Verified bearing thermal risk. Authorized load curtailment to 65%.');
  const [rejectReason, setRejectReason] = React.useState('');
  const [showRejectInput, setShowRejectInput] = React.useState(false);

  const statusBadge = {
    PENDING_APPROVAL: { color: 'text-yellow-400 border-yellow-500/40 bg-yellow-500/10', label: '⏳ PENDING APPROVAL' },
    APPROVED: { color: 'text-green-400 border-green-500/40 bg-green-500/10', label: '✅ APPROVED' },
    REJECTED: { color: 'text-red-400 border-red-500/40 bg-red-500/10', label: '🚫 REJECTED' },
    EXECUTED: { color: 'text-blue-400 border-blue-500/40 bg-blue-500/10', label: '▶ EXECUTED' },
  }[approval.status] ?? { color: 'text-gray-400 border-gray-600 bg-gray-700/50', label: approval.status };

  const isPending = approval.status === 'PENDING_APPROVAL';

  return (
    <div className="border border-yellow-500/30 bg-yellow-900/10 rounded-lg p-4 space-y-3">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <ShieldAlert className="text-yellow-400 shrink-0" size={18} />
          <div>
            <p className="text-white font-semibold text-sm font-mono">
              {approval.tool_name}
            </p>
            <p className="text-gray-500 text-[10px] font-mono">
              {approval.action_id} · plan: {approval.plan_id?.slice(0, 16)}...
            </p>
          </div>
        </div>
        <span className={`text-[10px] font-bold border rounded px-2 py-0.5 font-mono shrink-0 ${statusBadge.color}`}>
          {statusBadge.label}
        </span>
      </div>

      {/* ArmorIQ Hold Reason */}
      <div className="bg-gray-900/60 border border-gray-700 rounded p-2.5">
        <p className="text-[10px] text-yellow-400 font-mono uppercase tracking-widest mb-1">
          ⚠ ArmorIQ Governance Intercept Reason
        </p>
        <p className="text-gray-300 text-[11px] leading-relaxed">{approval.reason}</p>
      </div>

      {/* Arguments */}
      <div className="bg-gray-900/60 border border-gray-700 rounded p-2.5">
        <p className="text-[10px] text-gray-500 font-mono uppercase tracking-widest mb-1">
          Proposed Arguments
        </p>
        <pre className="text-orange-300 text-[11px] font-mono overflow-auto">
          {JSON.stringify(approval.arguments, null, 2)}
        </pre>
      </div>

      {/* Delegation ID */}
      <div className="flex items-center gap-1.5 text-[10px] text-gray-500 font-mono">
        <Shield size={10} />
        <span>delegation: {approval.delegation_id}</span>
        <span>·</span>
        <Clock size={10} />
        <span>{new Date(approval.created_at).toLocaleString()}</span>
      </div>

      {/* Reviewer info (if processed) */}
      {!isPending && approval.reviewed_by && (
        <div className="text-[11px] text-gray-400 font-mono border-t border-gray-700 pt-2">
          Reviewed by <span className="text-white">{approval.reviewed_by}</span>
          {approval.reviewed_at && <> on {new Date(approval.reviewed_at).toLocaleString()}</>}
          {approval.review_notes && <p className="text-gray-500 mt-0.5">"{approval.review_notes}"</p>}
        </div>
      )}

      {/* Action buttons */}
      {isPending && (
        <div className="space-y-2 border-t border-gray-700 pt-3">
          <div className="flex flex-col gap-1.5">
            <label className="text-[10px] text-gray-500 font-mono uppercase">Reviewer Identity</label>
            <input
              className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-[11px] text-white font-mono w-full focus:outline-none focus:border-orange-500"
              value={reviewer}
              onChange={(e) => setReviewer(e.target.value)}
              placeholder="reviewer@company.com"
            />
          </div>

          {!showRejectInput ? (
            <>
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] text-gray-500 font-mono uppercase">Approval Notes</label>
                <input
                  className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-[11px] text-white font-mono w-full focus:outline-none focus:border-orange-500"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Rationale for approval..."
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => onApprove(approval.action_id, reviewer, notes)}
                  disabled={isProcessing || !reviewer}
                  className="flex-1 flex items-center justify-center gap-1.5 bg-green-700/60 hover:bg-green-700 border border-green-500/50 text-green-300 rounded px-3 py-1.5 text-xs font-bold font-mono transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ShieldCheck size={12} />
                  APPROVE & EXECUTE
                </button>
                <button
                  onClick={() => setShowRejectInput(true)}
                  disabled={isProcessing}
                  className="flex items-center gap-1.5 bg-red-900/40 hover:bg-red-900/70 border border-red-500/40 text-red-400 rounded px-3 py-1.5 text-xs font-bold font-mono transition disabled:opacity-50"
                >
                  REJECT
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] text-gray-500 font-mono uppercase">Rejection Reason</label>
                <input
                  className="bg-gray-900 border border-red-700/50 rounded px-2 py-1 text-[11px] text-white font-mono w-full focus:outline-none focus:border-red-500"
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Reason for rejection..."
                  autoFocus
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => onReject(approval.action_id, reviewer, rejectReason || 'Rejected by supervisor')}
                  disabled={isProcessing}
                  className="flex-1 flex items-center justify-center gap-1.5 bg-red-800/60 hover:bg-red-800 border border-red-500/50 text-red-300 rounded px-3 py-1.5 text-xs font-bold font-mono transition"
                >
                  CONFIRM REJECTION
                </button>
                <button
                  onClick={() => setShowRejectInput(false)}
                  className="text-gray-500 hover:text-gray-300 px-3 py-1.5 text-xs font-mono transition"
                >
                  Cancel
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
