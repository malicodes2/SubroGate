import React, { useState } from 'react';
import { ShieldCheck, CheckCircle2, Loader2, PenTool, KeyRound, RotateCcw, Flag, Lock, Unlock } from 'lucide-react';
import { HumanApprovalEvent, CaseStatus } from '../types';

interface HumanApprovalSectionProps {
  caseId: string;
  caseStatus: CaseStatus;
  humanApprovals?: HumanApprovalEvent[];
  onApprove: (approval: HumanApprovalEvent) => Promise<void>;
  onRequestReanalysis?: () => void;
  onFlagManual?: () => void;
  isLoading?: boolean;
}

export const HumanApprovalSection: React.FC<HumanApprovalSectionProps> = ({
  caseId,
  caseStatus,
  humanApprovals = [],
  onApprove,
  onRequestReanalysis,
  onFlagManual,
  isLoading = false
}) => {
  const [adjusterName, setAdjusterName] = useState('Senior Adjuster Sarah Doe');
  const [liabilityPct, setLiabilityPct] = useState(100);
  const [notes, setNotes] = useState('Forensic custody overlap and clean origin EIR verified. Proceed with subrogation demand.');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  const isApproved = caseStatus === 'APPROVED' || caseStatus === 'NEGOTIATION' || caseStatus === 'RESOLVED';
  const latestApproval = humanApprovals[humanApprovals.length - 1];

  const handleApproveClick = async () => {
    if (!adjusterName.trim()) return;
    try {
      setIsSubmitting(true);
      setActionFeedback(null);
      const approval: HumanApprovalEvent = {
        approval_id: `APP-${Date.now().toString(36).toUpperCase()}`,
        adjuster_name: adjusterName.trim(),
        allocated_liability_pct: liabilityPct,
        notes: notes.trim(),
        audit_badge_token: `SIG-AUTH-${Math.random().toString(36).substring(2, 10).toUpperCase()}`
      };
      await onApprove(approval);
      setActionFeedback('Liability assessment authorized. Settlement Agent unlocked.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={`glass-card p-6 space-y-5 shadow-sm ${
      isApproved ? 'border-emerald-300' : 'border-blue-200'
    }`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center shadow-xs ${
            isApproved 
              ? 'bg-emerald-100 border border-emerald-300 text-emerald-700' 
              : 'bg-amber-100 border border-amber-300 text-amber-700'
          }`}>
            {isApproved ? <ShieldCheck className="w-4 h-4" /> : <PenTool className="w-4 h-4" />}
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              Human Claims Adjuster Review &amp; Approval Gate
              {isApproved ? (
                <span className="badge badge-green text-[10px]">
                  AUTHORIZED &amp; SIGNED
                </span>
              ) : (
                <span className="badge badge-amber text-[10px]">
                  REVIEW REQUIRED
                </span>
              )}
            </h3>
            <p className="text-xs text-slate-500">
              Mandatory human sign-off gate before subrogation demand or carrier negotiation
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-500 font-medium">Downstream Status:</span>
          <span className={`font-bold flex items-center gap-1 ${isApproved ? 'text-emerald-700' : 'text-amber-700'}`}>
            {isApproved ? (
              <>
                <Unlock className="w-3.5 h-3.5 text-emerald-600" />
                SETTLEMENT UNLOCKED
              </>
            ) : (
              <>
                <Lock className="w-3.5 h-3.5 text-amber-600" />
                AWAITING SIGN-OFF
              </>
            )}
          </span>
        </div>
      </div>

      {/* Review Checklist Summary (Light Mode) */}
      <div className="glass-inset p-4 rounded-lg bg-slate-50 border-slate-200">
        <span className="text-[11px] text-slate-600 uppercase tracking-wider block font-bold mb-2.5">
          ADJUSTER AUDIT CHECKLIST
        </span>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="flex items-center gap-2 text-slate-700 font-medium">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Timeline Reconstructed</span>
          </div>
          <div className="flex items-center gap-2 text-slate-700 font-medium">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Supporting EIR Verified</span>
          </div>
          <div className="flex items-center gap-2 text-slate-700 font-medium">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Defenses Evaluated</span>
          </div>
          <div className="flex items-center gap-2 text-slate-700 font-medium">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Recovery Grounded</span>
          </div>
        </div>
      </div>

      {/* Signed State Card */}
      {isApproved && latestApproval ? (
        <div className="glass-panel p-5 rounded-lg flex flex-col md:flex-row md:items-center justify-between gap-4 bg-emerald-50/50 border-emerald-200 shadow-xs">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-sm text-emerald-800 font-bold">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>Signed by Licensed Adjuster: <strong className="text-slate-900">{latestApproval.adjuster_name}</strong></span>
            </div>
            <p className="text-xs text-slate-700">
              Allocated Liability: <strong className="text-slate-900">{latestApproval.allocated_liability_pct}%</strong> • Notes: &ldquo;{latestApproval.notes}&rdquo;
            </p>
          </div>

          <div className="glass-inset px-3.5 py-2 rounded-lg text-xs font-mono shrink-0 flex items-center gap-2 bg-white border-slate-200 shadow-xs">
            <KeyRound className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-slate-500 text-[11px]">Audit Token:</span>
            <span className="text-slate-900 font-bold">{latestApproval.audit_badge_token}</span>
          </div>
        </div>
      ) : (
        /* Unapproved Form */
        <div className="space-y-4 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-slate-700 block text-xs font-bold mb-1.5">
                CLAIMS ADJUSTER NAME / ID *
              </label>
              <input
                type="text"
                value={adjusterName}
                onChange={(e) => setAdjusterName(e.target.value)}
                placeholder="e.g. Senior Adjuster Sarah Doe"
                className="w-full"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-slate-700 text-xs font-bold">
                  ALLOCATED LIABILITY ALLOCATION
                </label>
                <span className="text-blue-700 font-extrabold">{liabilityPct}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={liabilityPct}
                onChange={(e) => setLiabilityPct(Number(e.target.value))}
                className="w-full h-2 bg-slate-200 rounded appearance-none cursor-pointer accent-blue-600 mt-2"
              />
            </div>
          </div>

          <div>
            <label className="text-slate-700 block text-xs font-bold mb-1.5">
              ADJUSTER FORENSIC RATIONALE &amp; SETTLEMENT INSTRUCTIONS
            </label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Enter adjuster sign-off rationale..."
              className="w-full"
            />
          </div>

          {/* Action Buttons: Approve, Reanalyze, Flag */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-slate-200">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  setActionFeedback('Reanalysis requested. Telemetry thresholds re-queued.');
                  if (onRequestReanalysis) onRequestReanalysis();
                }}
                disabled={isSubmitting || isLoading}
                className="btn-secondary text-xs"
              >
                <RotateCcw className="w-3.5 h-3.5 text-blue-600" />
                <span>Request Reanalysis</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setActionFeedback('Case escalated for manual forensic audit.');
                  if (onFlagManual) onFlagManual();
                }}
                disabled={isSubmitting || isLoading}
                className="btn-secondary text-xs border-amber-300 text-amber-800 hover:bg-amber-50"
              >
                <Flag className="w-3.5 h-3.5 text-amber-600" />
                <span>Escalate for Manual Review</span>
              </button>
            </div>

            <button
              onClick={handleApproveClick}
              disabled={isSubmitting || isLoading || !adjusterName.trim()}
              className="btn-primary"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Locking Liability...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" />
                  <span>Approve Assessment &amp; Unlock Settlement</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {actionFeedback && (
        <div className="p-3 rounded glass-panel text-xs text-slate-800 flex items-center justify-between border-blue-200 bg-blue-50/70">
          <span>{actionFeedback}</span>
          <button onClick={() => setActionFeedback(null)} className="text-slate-500 hover:text-slate-800">✕</button>
        </div>
      )}
    </div>
  );
};
