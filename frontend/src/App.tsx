import React, { useState, useEffect } from 'react';
import { 
  Layers, 
  Clock, 
  Bot, 
  ShieldCheck, 
  Scale, 
  Loader2, 
  AlertTriangle,
  RotateCcw
} from 'lucide-react';
import { Navbar } from './components/Navbar';
import { LandingHero } from './components/LandingHero';
import { CaseHeader } from './components/CaseHeader';
import { NewInvestigationModal } from './components/NewInvestigationModal';
import { EvidenceSection } from './components/EvidenceSection';
import { TimelineSection } from './components/TimelineSection';
import { AssessmentSection } from './components/AssessmentSection';
import { HumanApprovalSection } from './components/HumanApprovalSection';
import { SettlementSection } from './components/SettlementSection';
import { TechnicalTraceDrawer } from './components/TechnicalTraceDrawer';
import { apiClient } from './api/client';
import { CaseModel, HealthResponse, HumanApprovalEvent } from './types';

export function App() {
  const [activeCase, setActiveCase] = useState<CaseModel | null>(null);
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // New Investigation Wizard Modal
  const [isNewModalOpen, setIsNewModalOpen] = useState<boolean>(false);

  // 5-Stage Primary Navigation (1: Evidence, 2: Reconstruction, 3: Assessment, 4: Human Review, 5: Recovery)
  const [activeStepTab, setActiveStepTab] = useState<number>(1);

  // Initial Load - Check live system health & model status (Starts with clean empty state)
  const initApp = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const health = await apiClient.checkHealth().catch(() => null);
      if (health) setHealthData(health);
    } catch (err: any) {
      console.warn('Initial system health check notice:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    initApp();
  }, []);

  // Poll in-flight case if background execution is active
  useEffect(() => {
    if (!activeCase || activeCase.status !== 'PROCESSING') return;

    const interval = setInterval(async () => {
      try {
        const updated = await apiClient.getCase(activeCase.case_id);
        if (updated && updated.status !== 'PROCESSING') {
          setActiveCase(updated);
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [activeCase?.case_id, activeCase?.status]);

  // Handler: Load Clean Demo Case
  const handleLoadCleanDemo = async () => {
    try {
      setActionLoading('Loading verified canonical demo case...');
      setError(null);
      const c = await apiClient.loadDemoCleanCase();
      setActiveCase(c);
      setActiveStepTab(1);
    } catch (err: any) {
      setError(`Failed to load demo case: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  // Handler: Simulate Failure Demo
  const handleLoadFailureDemo = async () => {
    try {
      setActionLoading('Loading unreadable EIR failure scenario...');
      setError(null);
      const c = await apiClient.loadDemoFailureCase();
      setActiveCase(c);
      setActiveStepTab(1);
    } catch (err: any) {
      setError(`Failed to load failure case: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  // Handler: Simulate IoT Stream Event
  const handleSimulateTelemetryStream = async () => {
    if (!activeCase) return;
    try {
      setActionLoading('Simulating 4.2G shock pulse stream event...');
      setError(null);
      await apiClient.simulateTelemetryEvent('SHOCK', activeCase.shipment_info?.container_id || 'MSKU9082345');
      const updated = await apiClient.getCase(activeCase.case_id);
      setActiveCase(updated);
    } catch (err: any) {
      setError(`Stream simulation error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  // Handler: Reset Demo State
  const handleResetDemo = async () => {
    try {
      setActionLoading('Resetting case state in Firestore...');
      setError(null);
      await apiClient.resetDemoState();
      await initApp();
    } catch (err: any) {
      setError(`Reset error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  // Handler: Human Adjuster Sign-Off
  const handleApproveCase = async (approval: HumanApprovalEvent) => {
    if (!activeCase) return;
    try {
      setActionLoading('Registering adjuster approval audit token...');
      const updated = await apiClient.approveLiability(activeCase.case_id, approval, activeCase.version);
      setActiveCase(updated);
      setActiveStepTab(5); // Jump directly to Settlement Workbench
    } catch (err: any) {
      setError(`Approval error: ${err.message}`);
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
    } catch (err: any) {
      setError(`Retry failed: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const isLiveAuth = Boolean(healthData?.model?.auth_configured);

  return (
    <div className="min-h-screen text-slate-900 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* Sleek Light Navigation Top Bar */}
      <Navbar
        modelInfo={healthData?.model}
        isConnected={!error && healthData !== null}
        onRefresh={initApp}
        onNewInvestigation={() => setIsNewModalOpen(true)}
        isLoading={isLoading}
        caseStatus={activeCase?.status}
        isLiveMode={isLiveAuth}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
        {/* Landing Hero (Light Welcome & Action Trigger) */}
        {!activeCase && (
          <LandingHero
            onStartNew={() => setIsNewModalOpen(true)}
            isLoading={isLoading || actionLoading !== null}
          />
        )}

        {/* Action Loading Banner */}
        {actionLoading && (
          <div className="glass-card p-3.5 border-blue-200 bg-blue-50/80 text-xs text-blue-800 flex items-center gap-2.5 shadow-xs animate-pulse">
            <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
            <span className="font-semibold">{actionLoading}</span>
          </div>
        )}

        {/* Background Processing Polling Banner */}
        {activeCase?.status === 'PROCESSING' && (
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

        {/* ACTIVE CASE WORKSPACE */}
        {activeCase && (
          <div className="space-y-6">
            {/* Minimalist Light Glass Case Header Ribbon */}
            <CaseHeader
              caseData={activeCase}
              onSimulateShock={handleSimulateTelemetryStream}
              onSimulateFailure={handleLoadFailureDemo}
              onReset={handleResetDemo}
              actionLoading={actionLoading}
            />

            {/* 5-STAGE NAVIGATION PILLS (Light Mode) */}
            <div className="glass-card p-1.5 border-slate-200 bg-white/90 shadow-sm">
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-1.5 text-xs">
                {[
                  { step: 1, label: '1. Evidence', icon: Layers, count: 'EIR + Telemetry' },
                  { step: 2, label: '2. Reconstruction', icon: Clock, count: 'Fused UTC' },
                  { step: 3, label: '3. Assessment', icon: Bot, count: '94% Confidence' },
                  { step: 4, label: '4. Human Review', icon: ShieldCheck, count: activeCase.status === 'APPROVED' ? 'Approved ✓' : 'Required' },
                  { step: 5, label: '5. Recovery', icon: Scale, count: 'Settlement Desk' }
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
              />
            )}

            {/* TAB 2: Reconstruction Timeline */}
            {activeStepTab === 2 && (
              <TimelineSection
                timeline={activeCase.normalized_timeline as any || []}
                responsibleParty={activeCase.shipment_info?.carrier_name}
              />
            )}

            {/* TAB 3: Evidence-Backed Responsibility Assessment */}
            {activeStepTab === 3 && (
              <AssessmentSection
                assessment={activeCase.assessment as any}
                responsibleParty={activeCase.shipment_info?.carrier_name}
                modelIdentifier={activeCase.model_identifier}
              />
            )}

            {/* TAB 4: Human Adjuster Approval Gate */}
            {activeStepTab === 4 && (
              <HumanApprovalSection
                caseId={activeCase.case_id}
                caseStatus={activeCase.status}
                humanApprovals={activeCase.human_approvals}
                onApprove={handleApproveCase}
                onRequestReanalysis={handleLoadCleanDemo}
                onFlagManual={() => setError('Case escalated for manual adjuster forensic audit.')}
              />
            )}

            {/* TAB 5: Settlement Agent & Negotiation Workbench */}
            {activeStepTab === 5 && (
              <SettlementSection
                caseId={activeCase.case_id}
                caseStatus={activeCase.status}
                onRefreshCase={initApp}
              />
            )}

            {/* Bottom Collapsible Technical Details / Execution Trace */}
            <TechnicalTraceDrawer caseId={activeCase.case_id} />
          </div>
        )}
      </main>

      {/* New Investigation Wizard Modal */}
      <NewInvestigationModal
        isOpen={isNewModalOpen}
        onClose={() => setIsNewModalOpen(false)}
        onCaseCreated={(created) => {
          setActiveCase(created);
          setActiveStepTab(1);
        }}
        isLiveMode={isLiveAuth}
      />
    </div>
  );
}

export default App;
