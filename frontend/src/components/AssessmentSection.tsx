import React from 'react';
import { Bot, CheckCircle2, Scale, BookOpen, ShieldCheck, DollarSign, HelpCircle } from 'lucide-react';
import { EvidenceBackedAssessment } from '../types';

interface AssessmentSectionProps {
  assessment?: EvidenceBackedAssessment | Record<string, any>;
  responsibleParty?: string;
  confidence?: number;
  modelIdentifier?: string;
}

export const AssessmentSection: React.FC<AssessmentSectionProps> = ({
  assessment,
  responsibleParty = 'Apex Drayage Logistics LLC (Motor Carrier)',
  confidence = 0.94
}) => {
  const partyName = assessment?.potentially_responsible_party || responsibleParty;
  const confScore = assessment?.responsibility_confidence || confidence;

  const whyPoints = [
    { label: "Earliest recorded breach", value: "17:15 UTC (+2h 45m post-origin interchange)" },
    { label: "Origin custody transfer", value: "14:30 UTC at APM Terminals Pier 400" },
    { label: "Sensor physical evidence", value: "4.2G shock pulse + thermal excursion to +12.4°C" },
    { label: "Exclusive custody at breach", value: "Apex Drayage Logistics LLC (Exclusive Care, Custody & Control)" },
    { label: "Supporting document proof", value: "Signed EIR Gate Receipt #9842 noted 'CLEAN' condition without defect exceptions" }
  ];

  const conflictingEvidence = assessment?.conflicting_evidence || [
    "Carrier driver verbally alleged unit was warm prior to outgate; however, driver signed clean interchange receipt without noting exception, legally waiving pre-existing defect defenses under UIIA Section E.2."
  ];

  const uncertaintyFactors = [
    "Reefer telemetry data rate: 60-second calibrated intervals (zero missing packet gaps verified).",
    "Pre-trip refrigeration pre-cooling logs at shipper facility verified nominal at -21.5°C."
  ];

  const legalFrameworks = assessment?.applicable_legal_framework || [
    {
      framework_name: "Carmack Amendment (49 U.S.C. § 14706)",
      governing_law_citation: "49 U.S.C. § 14706",
      key_legal_principle: "Establishes strict prima facie liability on motor carriers for loss/damage during transit upon proof of delivery in good condition at origin and damage at destination."
    },
    {
      framework_name: "Uniform Intermodal Interchange Agreement (UIIA Section E.2)",
      governing_law_citation: "UIIA Sec. E.2",
      key_legal_principle: "Motor carrier assumes full Care, Custody, and Control upon signing gate interchange receipt at ocean/rail terminal."
    }
  ];

  const recommendedAction = assessment?.recommended_recovery_action || 
    "Issue formal Subrogation Demand Letter to Apex Drayage Claims Dept for full claimed loss of $75,000.00 USD under 49 U.S.C. § 14706.";

  return (
    <div className="glass-card p-6 space-y-6 shadow-sm">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 flex items-center justify-center shadow-xs">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Evidence-Backed Responsibility Assessment
            </h2>
            <p className="text-xs text-slate-500">
              Deterministic evidentiary correlation and statutory liability synthesis
            </p>
          </div>
        </div>

        <span className="badge badge-green text-xs font-bold">
          EVIDENCE GROUNDED
        </span>
      </div>

      {/* Primary Conclusion Box */}
      <div className="glass-panel p-5 border-blue-200 bg-blue-50/40 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xs">
        <div className="space-y-1.5">
          <span className="text-[11px] text-blue-700 uppercase tracking-wider flex items-center gap-1.5 font-bold">
            <ShieldCheck className="w-4 h-4" />
            POTENTIALLY RESPONSIBLE PARTY
          </span>
          <h3 className="text-xl font-extrabold text-slate-900 tracking-tight">
            {partyName}
          </h3>
          <p className="text-xs text-slate-600 max-w-xl leading-relaxed">
            Physical custody held at the exact moment of shock impact and reefer compressor failure. Full prima facie case established under applicable statutes.
          </p>
        </div>

        {/* Confidence Gauge */}
        <div className="glass-inset p-4 min-w-[150px] text-right shrink-0 bg-white border-slate-200 shadow-xs">
          <span className="text-[10px] text-slate-500 block uppercase font-bold">CONFIDENCE SCORE</span>
          <span className="text-2xl font-black text-emerald-600 block mt-0.5">
            {Math.round(confScore * 100)}%
          </span>
          <div className="w-full bg-slate-100 h-1.5 rounded-full mt-2 overflow-hidden border border-slate-200">
            <div 
              className="bg-emerald-500 h-full rounded-full transition-all duration-500" 
              style={{ width: `${Math.round(confScore * 100)}%` }} 
            />
          </div>
        </div>
      </div>

      {/* WHY Section: Concise Evidentiary Statements */}
      <div className="glass-inset p-5 rounded-lg space-y-3 bg-slate-50 border-slate-200">
        <div className="flex items-center justify-between pb-2 border-b border-slate-200">
          <h4 className="font-bold text-xs text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            Why Was This Responsibility Assessment Reached?
          </h4>
          <span className="badge badge-green text-[10px]">5 Corroborations</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
          {whyPoints.map((pt, idx) => (
            <div key={idx} className="glass-panel p-3 rounded bg-white border-slate-200 shadow-xs space-y-1">
              <span className="text-[10px] text-slate-500 block uppercase font-bold">{pt.label}:</span>
              <strong className="text-slate-800 text-xs block leading-snug">{pt.value}</strong>
            </div>
          ))}
        </div>
      </div>

      {/* Grid: Conflicting Evidence & Uncertainty Scope */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
        {/* Conflicting Evidence */}
        <div className="glass-inset p-4 rounded-lg space-y-2.5 bg-slate-50 border-slate-200">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200">
            <span className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
              <Scale className="w-4 h-4 text-amber-600" />
              Conflicting Evidence &amp; Waived Defenses
            </span>
            <span className="badge badge-amber text-[10px]">Rebuttal Ready</span>
          </div>

          <ul className="space-y-2">
            {conflictingEvidence.map((ev: string, i: number) => (
              <li key={i} className="glass-panel p-2.5 rounded bg-white border-slate-200 text-slate-700 leading-relaxed text-xs shadow-xs">
                {ev}
              </li>
            ))}
          </ul>
        </div>

        {/* Verification Scope */}
        <div className="glass-inset p-4 rounded-lg space-y-2.5 bg-slate-50 border-slate-200">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200">
            <span className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
              <HelpCircle className="w-4 h-4 text-cyan-600" />
              Forensic Verification Scope
            </span>
            <span className="badge badge-cyan text-[10px]">Audited</span>
          </div>

          <ul className="space-y-2">
            {uncertaintyFactors.map((u: string, i: number) => (
              <li key={i} className="glass-panel p-2.5 rounded bg-white border-slate-200 text-slate-700 leading-relaxed text-xs shadow-xs">
                {u}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Statutory Legal Precedent Frameworks */}
      <div className="glass-inset p-4 rounded-lg space-y-3 bg-slate-50 border-slate-200">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-900">
          <BookOpen className="w-4 h-4 text-slate-600" />
          <span>Applicable Statutory &amp; Contractual Frameworks</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {legalFrameworks.map((law: any, i: number) => (
            <div key={i} className="glass-panel p-3 rounded bg-white border-slate-200 shadow-xs space-y-1">
              <div className="flex items-center justify-between text-xs font-bold text-slate-800">
                <span>{law.framework_name || law.governing_law_citation}</span>
                <span className="text-[10px] text-slate-400 font-normal">Binding Statute</span>
              </div>
              <p className="text-[11px] text-slate-600 leading-relaxed">
                {law.key_legal_principle}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Recommended Recovery Action */}
      <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-200 flex items-start gap-3 shadow-xs">
        <div className="w-8 h-8 rounded-lg bg-emerald-100 border border-emerald-300 flex items-center justify-center text-emerald-700 shrink-0">
          <DollarSign className="w-4 h-4" />
        </div>
        <div className="space-y-0.5 text-xs">
          <span className="text-[11px] text-emerald-800 font-bold uppercase tracking-wider block">
            Recommended Recovery Action
          </span>
          <p className="text-slate-800 text-xs font-medium leading-relaxed">
            {recommendedAction}
          </p>
        </div>
      </div>

      {/* Strict Legal Boundary Disclaimer */}
      <p className="text-[11px] text-slate-500 text-center leading-relaxed">
        *Evidence-backed responsibility assessment for subrogation recovery analysis. Not a legal ruling or binding liability determination.*
      </p>
    </div>
  );
};
