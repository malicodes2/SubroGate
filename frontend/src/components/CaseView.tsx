import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Layers, 
  Clock, 
  Bot, 
  ShieldCheck, 
  Scale, 
  Loader2, 
  AlertTriangle,
  RotateCcw,
  Terminal
} from 'lucide-react';
import { CaseHeader } from './CaseHeader';
import { EvidenceSection } from './EvidenceSection';
import { TimelineSection } from './TimelineSection';
import { AssessmentSection } from './AssessmentSection';
import { HumanApprovalSection } from './HumanApprovalSection';
import { SettlementSection } from './SettlementSection';
import { TechnicalTraceDrawer } from './TechnicalTraceDrawer';
import { ForensicReportTemplate } from './ForensicReportTemplate';
import { apiClient } from '../api/client';
import { CaseModel, HumanApprovalEvent } from '../types';

interface CaseViewProps {
  onCaseUpdated?: () => void;
}

export const CaseView: React.FC<CaseViewProps> = ({ onCaseUpdated }) => {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  
  const [activeCase, setActiveCase] = useState<CaseModel | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Technical Trace Modal
  const [isTraceOpen, setIsTraceOpen] = useState<boolean>(false);

  // 5-Stage Primary Navigation
  const [activeStepTab, setActiveStepTab] = useState<number>(1);

  // Load case on mount or when caseId changes
  const loadCase = async (id: string) => {
    try {
      setIsLoading(true);
      setError(null);
      const fetched = await apiClient.getCase(id);
      setActiveCase(fetched);
      
      // Auto-navigate tabs based on status
      if (
        fetched.status === 'APPROVED' || 
        fetched.status === 'AWAITING_RESPONSE' || 
        fetched.status === 'NEGOTIATION' || 
        fetched.status === 'RESOLVED'
      ) {
        setActiveStepTab(5);
      } else {
        // Start at Evidence (Tab 1) sequentially for all other statuses
        setActiveStepTab(1);
      }
    } catch (err: any) {
      setError(`Failed to load case: ${err.message}`);
      // navigate('/');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (caseId) {
      loadCase(caseId);
    }
  }, [caseId]);

  // Poll in-flight case if background execution is active
  useEffect(() => {
    if (!activeCase || activeCase.status !== 'ANALYZING') return;

    const interval = setInterval(async () => {
      try {
        const updated = await apiClient.getCase(activeCase.case_id);
        if (updated && updated.status !== 'ANALYZING') {
          setActiveCase(updated);
          if (onCaseUpdated) onCaseUpdated();
          
          if (updated.status === 'FAILED') {
            setError('Investigation flagged extraction issue.');
          }
          // Intentionally do NOT jump to tab 4 automatically,
          // so the user can read Tab 1 sequentially.
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [activeCase?.case_id, activeCase?.status]);


  const handleApproveCase = async (approval: HumanApprovalEvent) => {
    if (!activeCase) return;
    try {
      setActionLoading('Registering adjuster approval audit token...');
      const updated = await apiClient.approveLiability(activeCase.case_id, approval, activeCase.version);
      setActiveCase(updated);
      setActiveStepTab(5); // Jump directly to Settlement Workbench
      if (onCaseUpdated) onCaseUpdated();
    } catch (err: any) {
      setError(`Approval error: ${err.message}`);
      throw err;
    } finally {
      setActionLoading(null);
    }
  };

  // Handler: Retry Failed Case
  const handleRetryCase = async () => {
    if (!activeCase) return;
    try {
      setActionLoading('Retrying investigation pipeline...');
      const updated = await apiClient.retryCase(activeCase.case_id);
      setActiveCase(updated);
      if (onCaseUpdated) onCaseUpdated();
    } catch (err: any) {
      setError(`Retry failed: ${err.message}`);
      throw err;
    } finally {
      setActionLoading(null);
    }
  };

  // Handler: Reanalyze Case (Human Extraction Fallback)
  const handleReanalyzeCase = async (corrections: Record<string, any>) => {
    if (!activeCase) return;
    try {
      setActionLoading('Reanalyzing timeline with human corrections...');
      const updated = await apiClient.reanalyzeCase(activeCase.case_id, corrections);
      setActiveCase(updated);
      setActiveStepTab(3); // Jump to Assessment to view updated results
      if (onCaseUpdated) onCaseUpdated();
    } catch (err: any) {
      setError(`Reanalysis error: ${err.message}`);
      throw err;
    } finally {
      setActionLoading(null);
    }
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center p-12">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  if (!activeCase) {
    return (
      <div className="flex-1 flex items-center justify-center p-12 text-slate-500 text-sm">
        Case not found.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Action Loading Banner */}
      {actionLoading && (
        <div className="glass-card p-3.5 border-blue-200 bg-blue-50/80 text-xs text-blue-800 flex items-center gap-2.5 shadow-xs animate-pulse">
          <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
          <span className="font-semibold">{actionLoading}</span>
        </div>
      )}

      {/* Background Processing Polling Banner */}
      {activeCase?.status === 'ANALYZING' && (
        <div className="glass-card p-5 border-blue-300 bg-blue-50/90 text-blue-950 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-sm">
          <div className="flex items-center gap-3">
            <Loader2 className="w-5 h-5 animate-spin text-blue-600 shrink-0" />
            <div>
              <strong className="text-slate-900 block text-sm font-bold">Background Investigation in Progress</strong>
              <span className="text-slate-600">Extracting EIR &rarr; Normalizing UTC &rarr; Correlating Telemetry Breach &rarr; Assessing Liability...</span>
            </div>
          </div>
          <span className="badge badge-blue text-[11px] self-start sm:self-center font-bold">
            POLLING FIRESTORE STATE
          </span>
        </div>
      )}

      {/* Failure Scenario Banner */}
      {activeCase?.status === 'FAILED' && (
        <div className="glass-card p-5 border-red-300 bg-red-50 text-red-900 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-sm">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-600 shrink-0" />
            <div>
              <strong className="text-slate-900 block text-sm font-bold">Investigation Flagged Extraction Issue</strong>
              <span className="text-slate-600">Document extraction OCR failed checksum verification or unparseable gate stamp.</span>
            </div>
          </div>
          <button
            onClick={handleRetryCase}
            disabled={actionLoading !== null}
            className="btn-danger shadow-xs"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Retry Investigation</span>
          </button>
        </div>
      )}

      {/* Error Notification */}
      {error && (
        <div className="glass-card p-4 border-red-300 bg-red-50 text-red-900 text-xs flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
            <span className="font-semibold">{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-slate-500 hover:text-slate-800">✕</button>
        </div>
      )}

      {/* INTERACTIVE CASE WORKSPACE (Hidden during PDF print) */}
      <div className="interactive-case-view space-y-6">
        {/* Minimalist Light Glass Case Header Ribbon */}
        <CaseHeader
          caseData={activeCase}
          actionLoading={actionLoading}
        />

        {/* 5-STAGE NAVIGATION PILLS (Light Mode) */}
        <div className="glass-card p-1.5 border-slate-200 bg-white/90 shadow-sm">
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-1.5 text-xs">
            {[
              { step: 1, label: '1. Evidence', icon: Layers, count: 'EIR + Telemetry' },
              { step: 2, label: '2. Reconstruction', icon: Clock, count: 'Fused UTC' },
              {
                step: 3,
                label: '3. Assessment',
                icon: Bot,
                count: (() => {
                  const conf = activeCase.assessment?.confidence_score ?? activeCase.assessment?.responsibility_confidence ?? activeCase.assessment?.confidence ?? activeCase.assessment?.deterministic_overlap?.confidence;
                  if (conf !== undefined && conf !== null) {
                    const num = Number(conf);
                    return `${Math.round(num <= 1 ? num * 100 : num)}% Confidence`;
                  }
                  if (['ASSESSMENT_READY', 'HUMAN_REVIEW', 'APPROVED', 'AWAITING_RESPONSE', 'NEGOTIATION', 'RESOLVED'].includes(activeCase.status)) {
                    return 'Ready';
                  }
                  return 'Pending';
                })()
              },
              { step: 4, label: '4. Human Review', icon: ShieldCheck, count: activeCase.status === 'APPROVED' || activeCase.status === 'RESOLVED' ? 'Approved ✓' : 'Required' },
              { step: 5, label: '5. Recovery', icon: Scale, count: 'Demand Desk' }
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeStepTab === tab.step;
              return (
                <button
                  key={tab.step}
                  onClick={() => setActiveStepTab(tab.step)}
                  className={`py-2.5 px-3.5 rounded-lg flex items-center justify-between text-left transition-all ${
                    isActive
                      ? 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-bold shadow-md shadow-blue-500/20'
                      : 'text-slate-700 hover:text-slate-900 hover:bg-slate-100/80 font-medium'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    <Icon className="w-4 h-4 shrink-0" />
                    <span className="truncate">{tab.label}</span>
                  </div>
                  <span className={`text-[10px] hidden lg:inline ${isActive ? 'text-blue-100' : 'text-slate-400'}`}>
                    {tab.count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* TAB PANES */}

        {/* TAB 1: Evidence Section (Combined / EIR / Telemetry) */}
        {activeStepTab === 1 && (
          <EvidenceSection
            containerId={activeCase.shipment_info?.container_id}
            eirData={activeCase.extracted_custody_events}
            telemetryRef={activeCase.telemetry_ref}
            shipmentInfo={activeCase.shipment_info as any}
            onReanalyze={handleReanalyzeCase}
          />
        )}

        {/* TAB 2: Reconstruction Timeline */}
        {activeStepTab === 2 && (
          <TimelineSection
            timeline={activeCase.normalized_timeline as any || []}
          />
        )}

        {/* TAB 3: Evidence-Backed Responsibility Assessment */}
        {activeStepTab === 3 && (
          <AssessmentSection
            assessment={activeCase.assessment as any}
          />
        )}

        {/* TAB 4: Human Adjuster Approval Gate */}
        {activeStepTab === 4 && (
          <HumanApprovalSection
            caseId={activeCase.case_id}
            caseStatus={activeCase.status}
            humanApprovals={activeCase.human_approvals}
            onApprove={handleApproveCase}
            onRequestReanalysis={handleRetryCase}
            onFlagManual={() => setError('Case escalated for manual adjuster forensic audit.')}
          />
        )}

        {/* TAB 5: Settlement Agent & Negotiation Workbench */}
        {activeStepTab === 5 && (
          <SettlementSection
            caseId={activeCase.case_id}
            caseStatus={activeCase.status}
            onRefreshCase={() => loadCase(activeCase.case_id)}
            claimedLossUsd={activeCase.shipment_info?.claimed_loss_usd}
            declaredValueUsd={activeCase.shipment_info?.declared_value_usd}
            carrierName={activeCase.shipment_info?.carrier_name}
            containerId={activeCase.shipment_info?.container_id}
            commodity={activeCase.shipment_info?.commodity}
          />
        )}

        {/* Subtle Footer for Technical Trace */}
        <div className="flex justify-center pt-8 pb-4">
          <button 
            onClick={() => setIsTraceOpen(true)}
            className="text-xs font-mono text-slate-400 hover:text-slate-600 flex items-center gap-2 transition-colors"
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>View System Trace Log</span>
          </button>
        </div>

        <TechnicalTraceDrawer 
          caseId={activeCase.case_id} 
          isOpen={isTraceOpen}
          onClose={() => setIsTraceOpen(false)}
        />
      </div>

      {/* DEDICATED OFFICIAL PRINT TEMPLATE (Active only during print/PDF export) */}
      <ForensicReportTemplate caseData={activeCase} />
    </div>
  );
};
