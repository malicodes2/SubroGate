import React, { useState } from 'react';
import { Scale, Lock, Send, ShieldAlert, ShieldCheck, Sparkles, Loader2, CheckCircle2, AlertTriangle, Mail, Wrench, Edit3, XCircle, Clock } from 'lucide-react';
import { CarrierObjectionType, InboundCarrierMessage, OutboundDraft, CaseStatus } from '../types';
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
  const isUnlocked = caseStatus === 'APPROVED' || caseStatus === 'AWAITING_RESPONSE' || caseStatus === 'NEGOTIATION' || caseStatus === 'RESOLVED';

  const [inboundMessage, setInboundMessage] = useState<InboundCarrierMessage | null>(null);
  const [outboundDraft, setOutboundDraft] = useState<OutboundDraft | null>(null);

  const [isEditingDraft, setIsEditingDraft] = useState(false);
  const [editedBody, setEditedBody] = useState('');

  const [isDispatchingInitial, setIsDispatchingInitial] = useState(false);
  const [isSimulatingResponse, setIsSimulatingResponse] = useState(false);
  const [isDrafting, setIsDrafting] = useState(false);
  const [isSanitizing, setIsSanitizing] = useState(false);
  const [isDispatching, setIsDispatching] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // 1. Dispatch Initial Demand
  const handleDispatchInitialDemand = async () => {
    try {
      setIsDispatchingInitial(true);
      // In a real app this would call the backend to send the initial demand and update state to AWAITING_RESPONSE
      // For this hackathon demo, we'll simulate the state transition.
      // We will pretend the API updates the status.
      // (This requires a backend update endpoint or we just set local state, but we need onRefreshCase to reflect it)
      // Since we can't easily mock backend state here without an endpoint, we'll fetch a mock inbound message immediately to enter NEGOTIATION.
      // Or we can just use the generateCarrierObjectionSample to get the message.
      setStatusMessage('Initial demand dispatched. Agent entering persistent monitor mode.');

      // MOCK: Auto-receive response after 2 seconds to simulate async
      setTimeout(() => {
        handleReceiveResponse();
      }, 2000);

    } catch (e: any) {
      setStatusMessage(`Error: ${e.message}`);
    } finally {
      setIsDispatchingInitial(false);
    }
  };

  // 2. Mock: Receive Carrier Response (Transitions to Negotiation)
  const handleReceiveResponse = async () => {
    try {
      setIsSimulatingResponse(true);
      setStatusMessage(null);
      // Simulating the webhook waking up the agent
      const msg = await apiClient.generateCarrierObjectionSample(caseId, 'DAMAGE_BEFORE_PICKUP');
      setInboundMessage(msg);
      setOutboundDraft(null);

      // Auto-draft the response
      await handleDraftResponse(msg);
    } catch (e: any) {
      setStatusMessage(`Error: ${e.message}`);
    } finally {
      setIsSimulatingResponse(false);
    }
  };

  // 3. Generate Settlement Agent Rebuttal Draft
  const handleDraftResponse = async (inbound: InboundCarrierMessage) => {
    try {
      setIsDrafting(true);
      setStatusMessage(null);
      const draft = await apiClient.generateSettlementDraft(caseId, inbound);
      setOutboundDraft(draft);
      setEditedBody(draft.draft_body_markdown);
      setIsEditingDraft(false);
    } catch (e: any) {
      setStatusMessage(`Error: ${e.message}`);
    } finally {
      setIsDrafting(false);
    }
  };

  // 4. Apply Suggested Sanitization
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

  // 5. Approve & Dispatch Draft
  const handleApproveAndDispatch = async () => {
    if (!outboundDraft) return;
    try {
      setIsDispatching(true);
      await apiClient.approveDraft(outboundDraft.draft_id, 'Senior Adjuster Sarah Doe');
      await apiClient.runDraftSecurityCheck(outboundDraft.draft_id);
      await apiClient.dispatchDraft(caseId, outboundDraft.draft_id);
      setStatusMessage('Draft successfully dispatched. Negotiation resolved.');
      await onRefreshCase(); // Should trigger a refresh which sets state to RESOLVED ideally
    } catch (e: any) {
      setStatusMessage(`Dispatch failed: ${e.message}`);
    } finally {
      setIsDispatching(false);
    }
  };

  return (
    <div className="glass-card p-8 space-y-6 shadow-sm">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center shadow-xs ${isUnlocked
              ? 'bg-blue-50 border border-blue-200 text-blue-700'
              : 'bg-slate-100 border border-slate-200 text-slate-400'
            }`}>
            <Scale className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-black text-slate-900 flex items-center gap-2 uppercase tracking-tight">
              Recovery Agent Workflow
              {isUnlocked ? (
                <span className="badge badge-blue text-[10px] ml-2">
                  ACTIVE
                </span>
              ) : (
                <span className="badge badge-amber text-[10px] flex items-center gap-1 ml-2">
                  <Lock className="w-2.5 h-2.5" /> LOCKED
                </span>
              )}
            </h2>
            <p className="text-sm text-slate-500 font-medium">
              Persistent state-driven negotiation and asynchronous carrier correspondence
            </p>
          </div>
        </div>
      </div>

      {/* LOCKED STATE BANNER */}
      {!isUnlocked && (
        <div className="glass-inset p-8 text-center flex flex-col items-center justify-center space-y-3 rounded-lg bg-slate-50 border-slate-200">
          <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-700 shadow-xs">
            <Lock className="w-6 h-6" />
          </div>
          <h3 className="font-bold text-slate-900 text-base">
            Recovery Agent Locked Pending Assessment Approval
          </h3>
          <p className="text-xs text-slate-600 max-w-md leading-relaxed">
            The persistent recovery agent cannot initiate subrogation demands until a human adjuster has formally reviewed and signed off on the evidence-backed responsibility assessment.
          </p>
          <div className="text-[11px] text-amber-800 bg-amber-50 px-3.5 py-1.5 rounded-md border border-amber-300 font-semibold">
            Please complete the Human Review Gate in Step 4 to unlock.
          </div>
        </div>
      )}

      {/* UNLOCKED WORKFLOW */}
      {isUnlocked && (
        <div className="space-y-6">

          {/* State 1: Initial Dispatch */}
          {!inboundMessage && (
            <div className="glass-inset p-8 text-center rounded-lg space-y-4 bg-slate-50 border-slate-200 flex flex-col items-center">
              <div className="w-12 h-12 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center mb-2">
                <Send className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-lg text-slate-900">Initiate Persistent Recovery Agent</h3>
              <p className="text-sm text-slate-600 max-w-lg leading-relaxed">
                The Recovery Agent will dispatch the formal demand package to the carrier and enter a persistent, background monitoring state. It will automatically wake up and resume the state machine when the carrier responds.
              </p>

              {!isDispatchingInitial ? (
                <button
                  onClick={handleDispatchInitialDemand}
                  className="btn-primary mt-4 py-3 px-6 shadow-md"
                >
                  <Sparkles className="w-4 h-4 mr-2" />
                  Dispatch Demand &amp; Start Agent Monitor
                </button>
              ) : (
                <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg flex items-center gap-3 text-blue-800 text-sm mt-4">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                  <strong>Agent active:</strong> Monitoring designated webhook for carrier response...
                </div>
              )}

              {/* Hidden trigger for hackathon demo to mock a response arriving */}
              {isDispatchingInitial && (
                <div className="pt-4 mt-4 border-t border-slate-200 w-full flex justify-center">
                  <button onClick={handleReceiveResponse} className="text-[10px] text-slate-400 hover:text-slate-600 underline">
                    [Demo: Force trigger inbound carrier webhook]
                  </button>
                </div>
              )}
            </div>
          )}

          {/* State 2: Asynchronous Carrier Response Received */}
          {inboundMessage && (
            <div className="space-y-6 border-l-2 border-blue-400 pl-6 relative">
              <div className="absolute -left-[17px] top-4 w-8 h-8 rounded-full bg-blue-500 border-4 border-white flex items-center justify-center shadow-sm">
                <Mail className="w-3 h-3 text-white" />
              </div>

              <div className="glass-inset p-5 rounded-lg space-y-3 bg-slate-50 border-slate-200 shadow-sm">
                <div className="flex items-center justify-between pb-2 border-b border-slate-200 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500 font-semibold text-xs uppercase tracking-wider">Agent Resumed: Inbound Notice from</span>
                    <span className="font-bold text-slate-900 text-sm">{inboundMessage.sender_party}</span>
                  </div>
                  <span className="badge badge-amber text-[10px] uppercase font-bold tracking-widest">{inboundMessage.identified_objection}</span>
                </div>

                <div className="text-sm text-slate-700 glass-panel p-4 rounded bg-white border-slate-200 leading-relaxed shadow-xs">
                  <p className="font-bold text-slate-900 mb-2">{inboundMessage.subject}</p>
                  <p className="text-sm text-slate-700">{inboundMessage.body_text}</p>
                </div>

                <div className="flex items-center pt-2">
                  {isDrafting ? (
                    <div className="flex items-center gap-2 text-sm text-blue-700 font-bold">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Agent formulating evidentiary rebuttal...
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-sm text-emerald-700 font-bold">
                      <CheckCircle2 className="w-4 h-4" />
                      Rebuttal formulated from timeline evidence.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* State 3: Outbound Draft & Security Gate */}
          {outboundDraft && !isDrafting && (
            <div className="space-y-4 pt-4 border-t border-slate-200">

              <div className="flex items-center gap-2 mb-2">
                <h3 className="font-bold text-slate-900 uppercase tracking-widest text-sm">Agent Prepared Rebuttal</h3>
              </div>

              {/* Security Screening Gate Banner */}
              <div className={`p-4 rounded-lg border flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-xs ${outboundDraft.security_report?.verdict === 'BLOCK'
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
                    className="btn-secondary text-xs py-1.5 px-3 shrink-0 flex items-center gap-1.5 border-amber-300 text-amber-800 hover:bg-amber-100"
                  >
                    <Wrench className="w-3 h-3" />
                    <span>Apply Sanitization</span>
                  </button>
                )}
              </div>

              {/* Draft Body / Inline Editor */}
              <div className="glass-inset p-5 rounded-lg space-y-4 bg-slate-50 border-slate-200">
                <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                  <span className="font-bold text-slate-900 text-sm">
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
                    className="w-full font-mono text-sm text-slate-900 p-4 rounded bg-white border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                  />
                ) : (
                  <div className="text-sm text-slate-800 whitespace-pre-line glass-panel p-5 rounded bg-white border-slate-200 leading-relaxed overflow-y-auto shadow-xs border-l-4 border-l-blue-500">
                    {editedBody || outboundDraft.draft_body_markdown}
                  </div>
                )}

                {/* Evidence Citations Attached */}
                <div className="space-y-2 pt-2">
                  <span className="text-[10px] text-slate-500 uppercase tracking-widest block font-bold">
                    Attached Evidence Payload:
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {outboundDraft.relevant_evidence_citations.map((c, i) => (
                      <div key={i} className="glass-panel p-3 rounded bg-white border-slate-200 shadow-xs space-y-1">
                        <span className="text-blue-700 font-bold block text-xs">{c.source_reference}</span>
                        <span className="text-slate-600 text-[11px] leading-relaxed block">{c.relevance_explanation}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 3 Explicit Action Buttons: Approve, Edit, Reject */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-4 border-t border-slate-200 mt-4">
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
                      onClick={() => {
                        setOutboundDraft(null);
                        setInboundMessage(null);
                      }}
                      className="btn-secondary text-xs border-red-300 text-red-700 hover:bg-red-50"
                    >
                      <XCircle className="w-3.5 h-3.5 text-red-600" />
                      <span>Reject &amp; Reset</span>
                    </button>
                  </div>

                  <button
                    onClick={handleApproveAndDispatch}
                    disabled={isDispatching || outboundDraft.security_report?.verdict === 'BLOCK'}
                    className="btn-success shadow-sm py-2 px-5"
                  >
                    {isDispatching ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Dispatching...</span>
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4" />
                        <span className="font-bold">Approve &amp; Dispatch Rebuttal</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Status Message Notification */}
          {statusMessage && (
            <div className="p-3 rounded glass-panel text-xs text-slate-800 flex items-center justify-between bg-white border-slate-200 shadow-xs mt-4">
              <span className="font-semibold">{statusMessage}</span>
              <button onClick={() => setStatusMessage(null)} className="text-slate-500 hover:text-slate-800">✕</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
