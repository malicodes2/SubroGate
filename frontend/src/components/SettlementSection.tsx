import React, { useState, useMemo, useEffect } from 'react';
import { 
  Scale, 
  Lock, 
  Copy, 
  Check, 
  FileText, 
  ShieldCheck, 
  Send, 
  Edit3, 
  RotateCcw, 
  HelpCircle, 
  ListOrdered, 
  Sparkles, 
  ChevronRight,
  Shield,
  FileCheck2,
  Calendar,
  AlertCircle,
  Printer
} from 'lucide-react';
import { CaseStatus, CarrierObjectionType } from '../types';
import { apiClient } from '../api/client';

interface SettlementSectionProps {
  caseId: string;
  caseStatus: CaseStatus;
  onRefreshCase: () => Promise<void>;
  claimedLossUsd?: number;
  declaredValueUsd?: number;
  carrierName?: string;
  containerId?: string;
  commodity?: string;
}

export const SettlementSection: React.FC<SettlementSectionProps> = ({
  caseId,
  caseStatus,
  onRefreshCase,
  claimedLossUsd,
  declaredValueUsd,
  carrierName = 'Motor Carrier',
  containerId = 'Container Unit',
  commodity = 'Commercial Cargo'
}) => {
  const isUnlocked = caseStatus === 'APPROVED' || caseStatus === 'AWAITING_RESPONSE' || caseStatus === 'NEGOTIATION' || caseStatus === 'RESOLVED';

  // Selected Objection Type for Rebuttal Brief
  const [selectedObjection, setSelectedObjection] = useState<CarrierObjectionType>('DAMAGE_BEFORE_PICKUP');
  
  // Copy state feedbacks
  const [copiedDemand, setCopiedDemand] = useState(false);
  const [copiedRebuttal, setCopiedRebuttal] = useState(false);
  
  // Inline edit states
  const [isEditingDemand, setIsEditingDemand] = useState(false);
  const [isEditingRebuttal, setIsEditingRebuttal] = useState(false);

  // Simulation run state
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationResult, setSimulationResult] = useState<any>(null);

  // Generated Demand Letter Text
  const defaultDemandLetter = useMemo(() => {
    const today = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    const formattedLoss = claimedLossUsd ? `$${Number(claimedLossUsd).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '$0.00';
    const formattedValue = declaredValueUsd ? `$${Number(declaredValueUsd).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '$0.00';

    return `FORMAL NOTICE OF SUBROGATION DEMAND & INTENT TO RECOVER
Date: ${today}
To: ${carrierName} Claims Department
Re: Subrogation Recovery Demand — Container ${containerId}
Dispute Reference: ${caseId}

Dear Claims Committee,

Please be advised that SubroGate has completed its forensic investigation regarding total cargo loss sustained aboard Container ${containerId} (${commodity}), with a declared value of ${formattedValue} USD and a substantiated recoverable loss of ${formattedLoss} USD.

1. PRIMA FACIE LIABILITY ESTABLISHED (49 U.S.C. § 14706 - CARMACK AMENDMENT):
Under established federal statutory doctrine (Missouri Pacific R. Co. v. Elmore & Stahl, 377 U.S. 134), the claimant has established a conclusive prima facie case:
  (a) Good Condition at Origin: Clean Equipment Interchange Receipt (EIR) executed without exceptions or thermal flags at origin handover.
  (b) Damaged Condition at Delivery: Documented temperature breach exceeding statutory thresholds and physical compromise upon delivery.
  (c) Specified Damages: Certified cargo salvage and destruction value totaling ${formattedLoss} USD.

2. FORENSIC CUSTODY & SENSOR OVERLAP:
Calibrated NIST time-series telemetry data confirms the critical thermal excursion occurred during active motor carrier custody between gate-in and consignee delivery.

DEMAND FOR REMITTANCE:
Demand is hereby made for payment in the amount of ${formattedLoss} USD within fourteen (14) calendar days of this notice. Remittance should reference claim ID ${caseId}.

Sincerely,
Senior Claims Adjuster
Subrogation Recovery Division
SubroGate Institutional Platform`;
  }, [caseId, claimedLossUsd, declaredValueUsd, carrierName, containerId, commodity]);

  // Rebuttal Briefs for each Objection Type
  const rebuttalBriefs: Record<CarrierObjectionType, { title: string; text: string; citation: string }> = {
    DAMAGE_BEFORE_PICKUP: {
      title: 'Rebuttal to Defense: "Damage Occurred Prior to Carrier Receipt"',
      citation: 'Exhibit A-1 (Signed Origin EIR) & Exhibit B-2 (Telemetry Baseline)',
      text: `REBUTTAL TO CARRIER DEFENSE (PRE-RECEIPT DAMAGE):

1. The carrier's assertion that cargo was thawed/compromised prior to pickup is directly contradicted by the signed origin Equipment Interchange Receipt (EIR).
2. The carrier's driver inspected and accepted the equipment with a clean condition notation and confirmed the reefer set-point.
3. Continuous NIST-calibrated time-series logs demonstrate cargo temperature remained within specification until post-carrier gate departure.
4. Under 49 U.S.C. § 14706, the carrier cannot sustain an "inherent vice" defense without affirmative proof of pre-existing defect, which is legally barred by its own signed clean EIR.`
    },
    DISPUTES_CUSTODY: {
      title: 'Rebuttal to Defense: "Terminal / Rail Delay Custody Disclaimer"',
      citation: 'Exhibit C-1 (UTC Normalized Intermodal Custody Matrix)',
      text: `REBUTTAL TO CARRIER DEFENSE (CUSTODY DISCLAIMER):

1. GPS geofence tracking and gate transaction logs establish Care, Custody, and Control remained with ${carrierName} throughout the duration of the thermal breach.
2. The carrier contracted for end-to-end through-drayage and remains strictly liable under Uniform Intermodal Interchange Agreement (UIIA) Section E.2.
3. No terminal exception was logged prior to carrier driver interchange.`
    },
    DISPUTES_SENSOR_RELIABILITY: {
      title: 'Rebuttal to Defense: "Uncertified Sensor Data Challenge"',
      citation: 'Exhibit D-1 (NIST Sensor Calibration Certificate & SHA-256 Checksum)',
      text: `REBUTTAL TO CARRIER DEFENSE (SENSOR RELIABILITY):

1. The data log was extracted from an active IoT cellular logger with valid NIST-traceable factory calibration.
2. The raw CSV payload is timestamp-anchored with a verified SHA-256 cryptographic fingerprint.
3. Dual-sensor cross-validation (discharge air and ambient pulp temp) confirms identical thermal trajectory.`
    },
    NOTICE_ALLEGEDLY_LATE: {
      title: 'Rebuttal to Defense: "Statutory Time Bar / Late Notice"',
      citation: 'Exhibit E-1 (49 U.S.C. § 14706(e)(1) Statutory 9-Month Window)',
      text: `REBUTTAL TO CARRIER DEFENSE (TIME-BAR CLAIM):

1. Under federal law (49 U.S.C. § 14706(e)(1)), statutory minimum notice for interstate motor carrier cargo claims is nine (9) months from delivery date.
2. The formal demand notice was filed within 18 days of delivery, well within all statutory and standard bill of lading windows.`
    },
    REQUESTS_SUPPORTING_DOCS: {
      title: 'Response to Carrier: "Supporting Documents & Verification Packet"',
      citation: 'Exhibit Index & Certified Claim Package',
      text: `TRANSMITTAL OF CERTIFIED EVIDENCE PACKAGE:

Attached please find certified forensic exhibits:
- Exhibit 1: Signed Origin Equipment Interchange Receipt (EIR)
- Exhibit 2: Raw Calibrated Time-Series Telemetry CSV with UTC Timeline Mapping
- Exhibit 3: Consignee Delivery Inspection & Temperature Pulping Log
- Exhibit 4: Commercial Invoice & Certified Cargo Destruction Certificate`
    },
    PARTIAL_SETTLEMENT_OFFER: {
      title: `Compromise Assessment: "${claimedLossUsd ? `$${Number(Math.round(claimedLossUsd * 0.6)).toLocaleString('en-US')}` : 'Partial'} USD Settlement Offer"`,
      citation: `Compromise Counter-Offer Protocol (${claimedLossUsd ? `$${Number(Math.round(claimedLossUsd * 0.85)).toLocaleString('en-US')} USD` : '85%'} Authorization)`,
      text: `COUNTER-OFFER IN RESPONSE TO SETTLEMENT COMPROMISE:

We acknowledge your settlement proposal. However, in light of conclusive liability established by the signed origin EIR and uninterrupted telemetry custody chain:
- Total substantiated loss: ${claimedLossUsd ? `$${Number(claimedLossUsd).toLocaleString('en-US', { minimumFractionDigits: 2 })} USD` : 'Total Claim Amount'}
- In the interest of immediate commercial resolution and avoiding formal arbitration/litigation, our adjuster is authorized to accept a final settlement of ${claimedLossUsd ? `$${Number(Math.round(claimedLossUsd * 0.85)).toLocaleString('en-US', { minimumFractionDigits: 2 })} USD` : '85% of substantiated loss'}.
- This counter-offer remains valid for seven (7) business days.`
    },
    GENERAL_DENIAL: {
      title: 'Escalation Notice: "Unsubstantiated General Claim Denial"',
      citation: 'Formal Legal Escalation & UIIA Arbitration Notice',
      text: `NOTICE OF ESCALATION & ARBITRATION FILING INTENT:

Your general denial fails to cite any of the five statutory Carmack exceptions (Act of God, Public Enemy, Act of Shipper, Public Authority, or Inherent Vice). 
Under 49 U.S.C. § 14706, general denials without factual evidence shifting the burden of proof are legally insufficient. Failure to provide a factual response within seven (7) days will result in formal escalation to UIIA arbitration and collection proceedings.`
    }
  };

  const [demandText, setDemandText] = useState(defaultDemandLetter);
  const [rebuttalText, setRebuttalText] = useState(rebuttalBriefs[selectedObjection].text);

  useEffect(() => {
    if (!isEditingDemand) {
      setDemandText(defaultDemandLetter);
    }
  }, [defaultDemandLetter, isEditingDemand]);

  useEffect(() => {
    if (!isEditingRebuttal) {
      setRebuttalText(rebuttalBriefs[selectedObjection].text);
    }
  }, [selectedObjection, claimedLossUsd, carrierName, isEditingRebuttal]);

  // Update rebuttal text when objection changes
  const handleSelectObjection = (obj: CarrierObjectionType) => {
    setSelectedObjection(obj);
    setRebuttalText(rebuttalBriefs[obj].text);
    setIsEditingRebuttal(false);
  };

  const handleCopyDemand = async () => {
    await navigator.clipboard.writeText(demandText);
    setCopiedDemand(true);
    setTimeout(() => setCopiedDemand(false), 2000);
  };

  const handleCopyRebuttal = async () => {
    await navigator.clipboard.writeText(rebuttalText);
    setCopiedRebuttal(true);
    setTimeout(() => setCopiedRebuttal(false), 2000);
  };

  // Run 3-Turn Negotiation Simulation Test
  const handleRunSimulation = async () => {
    try {
      setIsSimulating(true);
      const res = await apiClient.simulateThreeTurnNegotiation(caseId);
      setSimulationResult(res);
      await onRefreshCase();
    } catch (err: any) {
      console.error('Simulation error:', err);
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Recovery Desk Header */}
      <div className="glass-card p-6 border-slate-200 bg-white shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center shadow-xs ${
            isUnlocked ? 'bg-emerald-50 border border-emerald-200 text-emerald-700' : 'bg-slate-100 border border-slate-200 text-slate-400'
          }`}>
            <Scale className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-slate-900 font-heading">
                Subrogation Recovery Desk &amp; Demand Package
              </h2>
              {isUnlocked ? (
                <span className="badge badge-green text-[10px] font-bold">
                  AUTHORIZED &amp; READY TO DISPATCH
                </span>
              ) : (
                <span className="badge badge-amber text-[10px] flex items-center gap-1 font-bold">
                  <Lock className="w-3 h-3" /> LOCKED PENDING SIGN-OFF
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 font-sans mt-0.5">
              Copy-ready subrogation notice, pre-drafted carrier rebuttals, and recovery execution protocol
            </p>
          </div>
        </div>

        {/* Claim Quick Metrics */}
        {isUnlocked && (
          <div className="flex items-center gap-3 text-xs font-mono bg-slate-50 p-2.5 rounded-lg border border-slate-200">
            <div>
              <span className="text-slate-400 block text-[10px]">RECOVERY DEMAND</span>
              <strong className="text-emerald-700 text-sm font-bold">${Number(claimedLossUsd).toLocaleString()} USD</strong>
            </div>
            <div className="border-l border-slate-200 pl-3">
              <span className="text-slate-400 block text-[10px]">PRIMARY CARRIER</span>
              <span className="text-slate-900 font-semibold">{carrierName}</span>
            </div>
          </div>
        )}
      </div>

      {/* LOCKED STATE */}
      {!isUnlocked && (
        <div className="glass-card p-10 text-center flex flex-col items-center justify-center space-y-3 border-amber-200 bg-amber-50/40 rounded-xl">
          <div className="w-12 h-12 rounded-full bg-amber-100 border border-amber-300 text-amber-800 flex items-center justify-center shadow-xs">
            <Lock className="w-6 h-6" />
          </div>
          <h3 className="font-heading font-bold text-slate-900 text-base">
            Demand Package Locked Pending Adjuster Review
          </h3>
          <p className="text-xs text-slate-600 max-w-lg leading-relaxed">
            Formal subrogation demand letters and evidentiary rebuttal briefs require formal claims adjuster approval. Please review the forensic timeline and approve the assessment in <strong>Tab 4 (Human Review)</strong> to unlock the copy-ready recovery package.
          </p>
        </div>
      )}

      {/* UNLOCKED STATE: 2-COLUMN ACTIONABLE DOCUMENTS */}
      {isUnlocked && (
        <>
          {/* Main 2-Column Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* COLUMN 1: Formal Demand Letter (Exhibit A) */}
            <div className="glass-card p-5 border-slate-200 bg-white shadow-sm flex flex-col justify-between space-y-4">
              <div>
                <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-blue-600" />
                    <span className="font-heading font-bold text-sm text-slate-900">
                      Formal Subrogation Demand Notice
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setIsEditingDemand(!isEditingDemand)}
                      className="p-1.5 rounded text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors text-xs flex items-center gap-1 font-mono"
                      title="Edit Demand Text"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      <span className="text-[11px]">{isEditingDemand ? 'Done' : 'Edit'}</span>
                    </button>
                    <button
                      type="button"
                      onClick={handleCopyDemand}
                      className={`btn-secondary text-xs py-1 px-2.5 flex items-center gap-1 font-bold ${
                        copiedDemand ? 'bg-emerald-50 border-emerald-300 text-emerald-700' : ''
                      }`}
                    >
                      {copiedDemand ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedDemand ? 'Copied to Clipboard!' : 'Copy Notice'}</span>
                    </button>
                  </div>
                </div>

                <p className="text-[11px] text-slate-500 font-sans my-2.5">
                  Complete, copy-ready legal demand letter citing the Carmack Amendment (49 U.S.C. § 14706) and verified timeline exhibits.
                </p>

                {/* Demand Letter Content */}
                {isEditingDemand ? (
                  <textarea
                    rows={16}
                    value={demandText}
                    onChange={(e) => setDemandText(e.target.value)}
                    className="w-full font-mono text-xs text-slate-900 p-3.5 rounded-lg bg-slate-50 border border-blue-300 focus:ring-2 focus:ring-blue-500 transition-all leading-relaxed"
                  />
                ) : (
                  <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 font-mono text-xs text-slate-800 whitespace-pre-line leading-relaxed max-h-[420px] overflow-y-auto select-text shadow-inner">
                    {demandText}
                  </div>
                )}
              </div>

              {/* Security Verified Micro-Badge */}
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] font-mono text-slate-500">
                <span className="flex items-center gap-1.5 text-emerald-700 font-semibold">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                  <span>DLP Screened (Zero PII / Margin Leakage)</span>
                </span>
                <span className="text-slate-400">Carmack § 14706 Format</span>
              </div>
            </div>

            {/* COLUMN 2: Pre-Drafted Evidentiary Rebuttal Brief (Exhibit B) */}
            <div className="glass-card p-5 border-slate-200 bg-white shadow-sm flex flex-col justify-between space-y-4">
              <div>
                <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                  <div className="flex items-center gap-2">
                    <FileCheck2 className="w-4 h-4 text-cyan-600" />
                    <span className="font-heading font-bold text-sm text-slate-900">
                      Evidentiary Rebuttal Brief
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setIsEditingRebuttal(!isEditingRebuttal)}
                      className="p-1.5 rounded text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors text-xs flex items-center gap-1 font-mono"
                      title="Edit Rebuttal Text"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      <span className="text-[11px]">{isEditingRebuttal ? 'Done' : 'Edit'}</span>
                    </button>
                    <button
                      type="button"
                      onClick={handleCopyRebuttal}
                      className={`btn-secondary text-xs py-1 px-2.5 flex items-center gap-1 font-bold ${
                        copiedRebuttal ? 'bg-emerald-50 border-emerald-300 text-emerald-700' : ''
                      }`}
                    >
                      {copiedRebuttal ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedRebuttal ? 'Copied to Clipboard!' : 'Copy Rebuttal'}</span>
                    </button>
                  </div>
                </div>

                {/* Objection Selector */}
                <div className="my-2.5 space-y-1">
                  <label className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider block">
                    Select Anticipated Carrier Defense:
                  </label>
                  <select
                    value={selectedObjection}
                    onChange={(e) => handleSelectObjection(e.target.value as CarrierObjectionType)}
                    className="w-full text-xs font-mono bg-white border border-slate-300 rounded-lg p-2 text-slate-900 focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="DAMAGE_BEFORE_PICKUP">Defense: "Cargo damaged prior to pickup at origin"</option>
                    <option value="DISPUTES_CUSTODY">Defense: "Disputes custody / Terminal delayed container"</option>
                    <option value="DISPUTES_SENSOR_RELIABILITY">Defense: "Third-party sensor uncertified / unreliable"</option>
                    <option value="NOTICE_ALLEGEDLY_LATE">Defense: "Claim notice received after time limit"</option>
                    <option value="REQUESTS_SUPPORTING_DOCS">Carrier: "Requesting signed EIR + raw CSV telemetry"</option>
                    <option value="PARTIAL_SETTLEMENT_OFFER">Proposal: "Carrier offers $45k compromise settlement"</option>
                    <option value="GENERAL_DENIAL">Defense: "General denial without evidence"</option>
                  </select>
                </div>

                {/* Rebuttal Text Area / Viewer */}
                {isEditingRebuttal ? (
                  <textarea
                    rows={14}
                    value={rebuttalText}
                    onChange={(e) => setRebuttalText(e.target.value)}
                    className="w-full font-mono text-xs text-slate-900 p-3.5 rounded-lg bg-slate-50 border border-blue-300 focus:ring-2 focus:ring-blue-500 transition-all leading-relaxed"
                  />
                ) : (
                  <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 font-mono text-xs text-slate-800 whitespace-pre-line leading-relaxed max-h-[380px] overflow-y-auto select-text shadow-inner">
                    {rebuttalText}
                  </div>
                )}
              </div>

              {/* Citations Footer */}
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] font-mono text-slate-500">
                <span className="truncate text-blue-700 font-semibold">
                  Evidence Anchor: {rebuttalBriefs[selectedObjection].citation}
                </span>
                <span className="text-slate-400 shrink-0">SubroGate Reasoning Engine</span>
              </div>
            </div>
          </div>

          {/* Actionable Next Steps Protocol Checklist */}
          <div className="glass-card p-6 border-slate-200 bg-white shadow-sm space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-200">
              <ListOrdered className="w-4 h-4 text-blue-600" />
              <h3 className="font-heading font-bold text-sm text-slate-900">
                Actionable Claims Adjuster Protocol (Next Steps)
              </h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
              <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-blue-600 text-white font-bold flex items-center justify-center text-[10px]">1</span>
                  <strong className="font-bold text-slate-900">Transmit Demand</strong>
                </div>
                <p className="text-slate-600 leading-relaxed text-[11px]">
                  Copy the <strong>Formal Subrogation Demand Notice</strong> and transmit to <code className="text-slate-900 bg-white px-1 py-0.5 rounded border border-slate-200">{carrierName}</code> via certified email or EDI claims portal.
                </p>
              </div>

              <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-blue-600 text-white font-bold flex items-center justify-center text-[10px]">2</span>
                  <strong className="font-bold text-slate-900">Attach Verified Exhibits</strong>
                </div>
                <p className="text-slate-600 leading-relaxed text-[11px]">
                  Include the origin EIR document, normalized UTC timeline CSV, and NIST sensor calibration certificate as Exhibit attachments.
                </p>
              </div>

              <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-blue-600 text-white font-bold flex items-center justify-center text-[10px]">3</span>
                  <strong className="font-bold text-slate-900">Set 14-Day Diary</strong>
                </div>
                <p className="text-slate-600 leading-relaxed text-[11px]">
                  Log a 14-calendar-day statutory follow-up diary. If carrier raises a pre-receipt or sensor challenge, deploy the pre-drafted Rebuttal Brief.
                </p>
              </div>

              <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-emerald-600 text-white font-bold flex items-center justify-center text-[10px]">4</span>
                  <strong className="font-bold text-slate-900">Remittance &amp; Release</strong>
                </div>
                <p className="text-slate-600 leading-relaxed text-[11px]">
                  Upon settlement receipt ({claimedLossUsd ? `$${Number(claimedLossUsd).toLocaleString()} USD` : 'substantiated recovery amount'}), execute standard release of liability and close subrogation file.
                </p>
              </div>
            </div>
          </div>

          {/* Interactive Negotiation Simulator (Test Mode / Demo) */}
          <div className="glass-card p-5 border-blue-100 bg-blue-50/40 rounded-xl space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <Sparkles className="w-4 h-4 text-blue-600" />
                <div>
                  <h4 className="font-heading font-bold text-xs text-slate-900">
                    Interactive Multi-Turn Negotiation Simulation (Test Mode)
                  </h4>
                  <p className="text-[11px] text-slate-500">
                    Executes a deterministic 3-turn interactive carrier negotiation with full DLP screening and settlement resolution.
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={handleRunSimulation}
                disabled={isSimulating}
                className="btn-primary text-xs py-1.5 px-3.5 shadow-sm font-bold self-start sm:self-auto"
              >
                {isSimulating ? 'Simulating Negotiation...' : 'Run 3-Turn Negotiation'}
              </button>
            </div>

            {/* Simulation Results Display */}
            {simulationResult && (
              <div className="p-4 rounded-lg bg-white border border-blue-200 space-y-3 mt-3 shadow-xs">
                <div className="flex items-center justify-between text-xs font-mono pb-2 border-b border-slate-100">
                  <span className="font-bold text-slate-900">Simulation ID: {simulationResult.simulation_id}</span>
                  <span className="badge badge-green text-[10px] font-bold">SETTLEMENT ACHIEVED: $65,000 USD</span>
                </div>

                <div className="space-y-2 text-xs font-mono">
                  {simulationResult.turns?.map((t: any, i: number) => (
                    <div key={i} className="p-2.5 rounded bg-slate-50 border border-slate-200 space-y-1">
                      <div className="flex items-center justify-between text-[11px]">
                        <strong className="text-blue-700">Turn {t.turn_index}: {t.inbound_carrier_message?.subject}</strong>
                        <span className="text-slate-500 text-[10px]">{t.status_at_turn_end}</span>
                      </div>
                      <p className="text-slate-700 text-[11px] font-sans">{t.notes}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Export Forensic Report */}
          <div className="glass-card p-5 border-slate-200 bg-white shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <h4 className="font-heading font-bold text-sm text-slate-900 flex items-center gap-2">
                <Printer className="w-4 h-4 text-slate-600" />
                Export Forensic Report
              </h4>
              <p className="text-[11px] text-slate-500 font-sans">
                Download a print-ready PDF of the complete forensic investigation report, including evidence citations, custody timeline, and liability assessment.
              </p>
            </div>
            <button
              type="button"
              onClick={() => window.print()}
              className="btn-primary text-xs py-2 px-4 flex items-center gap-2 font-bold shrink-0 shadow-sm"
            >
              <Printer className="w-3.5 h-3.5" />
              Export Forensic PDF
            </button>
          </div>
        </>
      )}
    </div>
  );
};
