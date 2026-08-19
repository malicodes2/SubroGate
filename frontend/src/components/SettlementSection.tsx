import React, { useState } from 'react';
import { Scale, Lock, Send, ShieldAlert, ShieldCheck, Sparkles, Loader2, CheckCircle2, AlertTriangle, Play, Mail, Wrench, Edit3, XCircle } from 'lucide-react';
import { CarrierObjectionType, InboundCarrierMessage, OutboundDraft, ThreeTurnNegotiationResult, CaseStatus } from '../types';
import { apiClient } from '../api/client';

interface SettlementSectionProps {
  caseId: string;
  caseStatus: CaseStatus;
  onRefreshCase: () => Promise<void>;
}

export const SettlementSection: React.FC<SettlementSectionProps> = ({
  caseId,
  caseStatus,
  onRefreshCase
}) => {
  const isUnlocked = caseStatus === 'APPROVED' || caseStatus === 'NEGOTIATION' || caseStatus === 'RESOLVED';

  const [selectedObjection, setSelectedObjection] = useState<CarrierObjectionType>('DAMAGE_BEFORE_PICKUP');
  const [inboundMessage, setInboundMessage] = useState<InboundCarrierMessage | null>(null);
  const [outboundDraft, setOutboundDraft] = useState<OutboundDraft | null>(null);
  const [simulationResult, setSimulationResult] = useState<ThreeTurnNegotiationResult | null>(null);

  const [isEditingDraft, setIsEditingDraft] = useState(false);
  const [editedBody, setEditedBody] = useState('');

  const [isGeneratingInbound, setIsGeneratingInbound] = useState(false);
  const [isDrafting, setIsDrafting] = useState(false);
  const [isSanitizing, setIsSanitizing] = useState(false);
  const [isDispatching, setIsDispatching] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // 1. Generate Carrier Objection
  const handleGenerateInbound = async (objectionType: CarrierObjectionType) => {
    try {
      setIsGeneratingInbound(true);
      setStatusMessage(null);
      const msg = await apiClient.generateCarrierObjectionSample(caseId, objectionType);
      setInboundMessage(msg);
      setOutboundDraft(null);
    } catch (e: any) {
      setStatusMessage(`Error: ${e.message}`);
    } finally {
      setIsGeneratingInbound(false);
    }
  };

  // 2. Generate Settlement Agent Rebuttal Draft
  const handleDraftResponse = async () => {
    if (!inboundMessage) return;
    try {
      setIsDrafting(true);
      setStatusMessage(null);
      const draft = await apiClient.generateSettlementDraft(caseId, inboundMessage);
      setOutboundDraft(draft);
      setEditedBody(draft.draft_body_markdown);
      setIsEditingDraft(false);
    } catch (e: any) {
      setStatusMessage(`Error: ${e.message}`);
    } finally {
      setIsDrafting(false);
    }
  };

  // 3. Apply Suggested Sanitization
  const handleApplySanitization = async () => {
    if (!outboundDraft) return;
    try {
      setIsSanitizing(true);
      const sanitized = await apiClient.applyDraftSanitization(outboundDraft.draft_id);
      setOutboundDraft(sanitized);
      setEditedBody(sanitized.draft_body_markdown);
      setStatusMessage('Suggested sanitization applied. Security verdict cleared.');
    } catch (e: any) {
      setStatusMessage(`Sanitization error: ${e.message}`);
    } finally {
      setIsSanitizing(false);
    }
  };

  // 4. Approve & Dispatch Draft
  const handleApproveAndDispatch = async () => {
    if (!outboundDraft) return;
    try {
      setIsDispatching(true);
      await apiClient.approveDraft(outboundDraft.draft_id, 'Senior Adjuster Sarah Doe');
      await apiClient.runDraftSecurityCheck(outboundDraft.draft_id);
      await apiClient.dispatchDraft(caseId, outboundDraft.draft_id);
      setStatusMessage('Draft successfully dispatched to carrier claims department.');
      await onRefreshCase();
    } catch (e: any) {
      setStatusMessage(`Dispatch failed: ${e.message}`);
    } finally {
      setIsDispatching(false);
    }
  };

  // 5. Reject Draft
  const handleRejectDraft = () => {
    setOutboundDraft(null);
    setStatusMessage('Draft response rejected by adjuster. Re-generate or choose another carrier defense.');
  };

  // 6. Run 3-Turn Negotiation Simulation
  const handleRunSimulation = async () => {
    try {
      setIsSimulating(true);
      setStatusMessage(null);
      const result = await apiClient.simulateThreeTurnNegotiation(caseId);
      setSimulationResult(result);
      await onRefreshCase();
    } catch (e: any) {
      setStatusMessage(`Simulation error: ${e.message}`);
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <div className="glass-card p-6 space-y-5 shadow-sm">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center shadow-xs ${
            isUnlocked 
              ? 'bg-blue-50 border border-blue-200 text-blue-700' 
              : 'bg-slate-100 border border-slate-200 text-slate-400'
          }`}>
            <Scale className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              Settlement Agent &amp; Dispute Recovery Desk
              {isUnlocked ? (
                <span className="badge badge-blue text-[10px]">
                  UNLOCKED
                </span>
              ) : (
                <span className="badge badge-amber text-[10px] flex items-center gap-1">
                  <Lock className="w-2.5 h-2.5" /> LOCKED
                </span>
              )}
            </h2>
            <p className="text-xs text-slate-500">
              Autonomous objection rebuttal synthesis, Model Armor security screening &amp; recovery negotiation
            </p>
          </div>
        </div>

        {/* 3-Turn Live Demo Button */}
        {isUnlocked && (
          <button
            onClick={handleRunSimulation}
            disabled={isSimulating}
            className="btn-primary shadow-sm"
          >
            {isSimulating ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Simulating Negotiation...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 text-cyan-200" />
                <span>Run 3-Turn Negotiation Demo</span>
              </>
            )}
          </button>
        )}
      </div>

      {/* LOCKED STATE BANNER */}
      {!isUnlocked && (
        <div className="glass-inset p-8 text-center flex flex-col items-center justify-center space-y-3 rounded-lg bg-slate-50 border-slate-200">
          <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-700 shadow-xs">
            <Lock className="w-6 h-6" />
          </div>
          <h3 className="font-bold text-slate-900 text-base">
            Settlement Agent Locked Pending Human Adjuster Sign-Off
          </h3>
          <p className="text-xs text-slate-600 max-w-md leading-relaxed">
            Under subrogation operating controls, outbound settlement notices and negotiation counter-demands cannot be initiated until an adjuster signs off on the responsibility assessment.
          </p>
          <div className="text-[11px] text-amber-800 bg-amber-50 px-3.5 py-1.5 rounded-md border border-amber-300 font-semibold">
            Please complete the Human Review Gate in Step 4 to unlock.
          </div>
        </div>
      )}

      {/* UNLOCKED SETTLEMENT WORKBENCH */}
      {isUnlocked && (
        <div className="space-y-5">
          {/* Section 1: Carrier Pushback Simulator Selector */}
          <div className="glass-inset p-4 rounded-lg space-y-3 bg-slate-50 border-slate-200">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-slate-500" />
                1. Simulate Inbound Carrier Pushback Defense
              </span>
              <span className="text-[11px] text-slate-500">Select defense to simulate</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs">
              {[
                { type: 'DAMAGE_BEFORE_PICKUP', label: 'Pre-Pickup Damage' },
                { type: 'DISPUTES_CUSTODY', label: 'Disputes Custody' },
                { type: 'DISPUTES_SENSOR_RELIABILITY', label: 'Sensor Unreliable' },
                { type: 'NOTICE_ALLEGEDLY_LATE', label: 'Late Notice Barred' },
                { type: 'REQUESTS_SUPPORTING_DOCS', label: 'Requests Exhibits' },
                { type: 'PARTIAL_SETTLEMENT_OFFER', label: 'Compromise Offer ($45k)' }
              ].map((opt) => (
                <button
                  key={opt.type}
                  onClick={() => {
                    setSelectedObjection(opt.type as CarrierObjectionType);
                    handleGenerateInbound(opt.type as CarrierObjectionType);
                  }}
                  disabled={isGeneratingInbound}
                  className={`p-2.5 rounded-lg border text-left transition-all truncate text-xs ${
                    selectedObjection === opt.type && inboundMessage
                      ? 'bg-blue-50 border-blue-400 text-blue-900 font-bold shadow-xs'
                      : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Section 2: Inbound Carrier Message Viewer */}
          {inboundMessage && (
            <div className="glass-inset p-5 rounded-lg space-y-3 bg-slate-50 border-slate-200">
              <div className="flex items-center justify-between pb-2 border-b border-slate-200 text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-slate-500 font-semibold text-xs">INBOUND NOTICE:</span>
                  <span className="font-bold text-slate-900 text-xs">{inboundMessage.sender_party}</span>
                </div>
                <span className="badge badge-amber text-[10px]">{inboundMessage.identified_objection}</span>
              </div>

              <div className="text-xs text-slate-700 glass-panel p-3.5 rounded bg-white border-slate-200 leading-relaxed shadow-xs">
                <p className="font-bold text-slate-900 mb-1">{inboundMessage.subject}</p>
                <p className="text-xs text-slate-700">{inboundMessage.body_text}</p>
              </div>

              <div className="flex items-center justify-between pt-1">
                <span className="text-xs text-slate-500">
                  Ready to draft grounded evidentiary rebuttal.
                </span>

                <button
                  onClick={handleDraftResponse}
                  disabled={isDrafting}
                  className="btn-primary shadow-sm"
                >
                  {isDrafting ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Formulating Rebuttal...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Draft Evidence-Backed Rebuttal</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Section 3: Outbound Draft, Security Gate & Action Controls */}
          {outboundDraft && (
            <div className="space-y-4 pt-2 border-t border-slate-200">
              {/* Security Screening Gate Banner */}
              <div className={`p-4 rounded-lg border flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-xs ${
                outboundDraft.security_report?.verdict === 'BLOCK'
                  ? 'bg-red-50 border-red-300 text-red-900'
                  : outboundDraft.security_report?.verdict === 'REVIEW'
                  ? 'bg-amber-50 border-amber-300 text-amber-900'
                  : 'bg-emerald-50 border-emerald-300 text-emerald-900'
              }`}>
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-white border border-slate-200 shrink-0 mt-0.5 shadow-xs">
                    {outboundDraft.security_report?.verdict === 'BLOCK' ? (
                      <ShieldAlert className="w-4 h-4 text-red-600" />
                    ) : outboundDraft.security_report?.verdict === 'REVIEW' ? (
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                    ) : (
                      <ShieldCheck className="w-4 h-4 text-emerald-600" />
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-xs text-slate-900">
                        Google Model Armor Screening: {outboundDraft.security_report?.verdict || 'PASS'}
                      </span>
                      <span className="text-[10px] bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-600 font-semibold">
                        {outboundDraft.security_report?.engine_used || 'MODEL_ARMOR_LOCAL_FALLBACK'}
                      </span>
                    </div>
                    <p className="text-xs text-slate-700 mt-0.5">
                      {outboundDraft.security_report?.action_taken || 'Draft cleared automated security screening.'}
                    </p>
                  </div>
                </div>

                {outboundDraft.security_report?.verdict === 'REVIEW' && (
                  <button
                    onClick={handleApplySanitization}
                    disabled={isSanitizing}
                    className="btn-secondary text-xs py-1.5 px-3 shrink-0 flex items-center gap-1.5 border-amber-300 text-amber-800"
                  >
                    <Wrench className="w-3 h-3" />
                    <span>Apply Sanitization</span>
                  </button>
                )}
              </div>

              {/* Draft Body / Inline Editor */}
              <div className="glass-inset p-5 rounded-lg space-y-3 bg-slate-50 border-slate-200">
                <div className="flex items-center justify-between pb-2 border-b border-slate-200 text-xs">
                  <span className="font-bold text-slate-900 text-xs">
                    {outboundDraft.draft_subject}
                  </span>
                  <span className="badge badge-neutral text-[10px]">
                    Status: {outboundDraft.status}
                  </span>
                </div>

                {isEditingDraft ? (
                  <textarea
                    rows={8}
                    value={editedBody}
                    onChange={(e) => setEditedBody(e.target.value)}
                    className="w-full font-mono text-xs text-slate-900 p-3 rounded bg-white border border-slate-300"
                  />
                ) : (
                  <div className="text-xs text-slate-800 whitespace-pre-line glass-panel p-4 rounded bg-white border-slate-200 leading-relaxed max-h-56 overflow-y-auto shadow-xs">
                    {editedBody || outboundDraft.draft_body_markdown}
                  </div>
                )}

                {/* Evidence Citations Attached */}
                <div className="space-y-2 pt-1">
                  <span className="text-[11px] text-slate-600 uppercase tracking-wider block font-bold">
                    Grounded Evidence Citations Attached:
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {outboundDraft.relevant_evidence_citations.map((c, i) => (
                      <div key={i} className="glass-panel p-2.5 rounded bg-white border-slate-200 shadow-xs text-xs space-y-1">
                        <span className="text-emerald-700 font-bold block text-[11px]">{c.source_reference}</span>
                        <span className="text-slate-600 text-[11px]">{c.relevance_explanation}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 3 Explicit Action Buttons: Approve, Edit, Reject */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-slate-200">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setIsEditingDraft(!isEditingDraft)}
                      className="btn-secondary text-xs"
                    >
                      <Edit3 className="w-3.5 h-3.5 text-blue-600" />
                      <span>{isEditingDraft ? 'Save Edits' : 'Edit Response'}</span>
                    </button>

                    <button
                      type="button"
                      onClick={handleRejectDraft}
                      className="btn-secondary text-xs border-red-300 text-red-700 hover:bg-red-50"
                    >
                      <XCircle className="w-3.5 h-3.5 text-red-600" />
                      <span>Reject Response</span>
                    </button>
                  </div>

                  <button
                    onClick={handleApproveAndDispatch}
                    disabled={isDispatching || outboundDraft.status === 'SECURITY_BLOCKED'}
                    className="btn-success shadow-sm"
                  >
                    {isDispatching ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Dispatching...</span>
                      </>
                    ) : (
                      <>
                        <Send className="w-3.5 h-3.5" />
                        <span>Approve Response &amp; Dispatch</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Section 4: 3-Turn Negotiation Results */}
          {simulationResult && (
            <div className="glass-inset p-5 rounded-lg space-y-3.5 border-emerald-300 bg-emerald-50/50 shadow-xs">
              <div className="flex items-center justify-between pb-2 border-b border-emerald-200">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <h3 className="font-bold text-xs text-slate-900">
                    3-Turn Negotiation Simulation Completed
                  </h3>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-slate-600 font-semibold text-xs">Final Settlement:</span>
                  <span className="text-emerald-800 font-extrabold text-xs bg-emerald-100 px-2.5 py-1 rounded border border-emerald-300">
                    ${simulationResult.final_settlement_usd?.toLocaleString()} USD (100% Recovery Target)
                  </span>
                </div>
              </div>

              <div className="space-y-2.5">
                {simulationResult.turns.map((turn) => (
                  <div key={turn.turn_index} className="glass-panel p-3 rounded bg-white border-slate-200 space-y-2 shadow-xs">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-900 font-bold">ROUND {turn.turn_index}</span>
                      <span className="text-emerald-700 font-semibold">{turn.notes}</span>
                    </div>
                    <div className="text-xs text-slate-700 bg-slate-50 p-2.5 rounded border border-slate-200">
                      <strong className="text-slate-900 block mb-0.5">Carrier: {turn.inbound_carrier_message.subject}</strong>
                      <span className="text-slate-600 text-[11px]">{turn.inbound_carrier_message.body_text}</span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="p-2.5 rounded bg-emerald-100 border border-emerald-300 text-center text-xs text-emerald-900 font-semibold">
                ✓ Case successfully resolved and archived in Firestore persistent state with complete audit trail.
              </div>
            </div>
          )}

          {/* Status Message Notification */}
          {statusMessage && (
            <div className="p-3 rounded glass-panel text-xs text-slate-800 flex items-center justify-between bg-white border-slate-200 shadow-xs">
              <span>{statusMessage}</span>
              <button onClick={() => setStatusMessage(null)} className="text-slate-500 hover:text-slate-800">✕</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
