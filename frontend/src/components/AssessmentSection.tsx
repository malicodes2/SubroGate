import React from 'react';
import { ShieldCheck, Bot, CheckCircle2, AlertTriangle, HelpCircle, BookOpen, ChevronRight, DollarSign } from 'lucide-react';
import { EvidenceBackedAssessment } from '../types';

interface AssessmentSectionProps {
  assessment?: EvidenceBackedAssessment | Record<string, any>;
  responsibleParty?: string;
  confidence?: number;
}

export const AssessmentSection: React.FC<AssessmentSectionProps> = ({
  assessment,
  responsibleParty = 'Apex Drayage Logistics LLC (Motor Carrier)',
  confidence = 0.94
}) => {
  const partyName = assessment?.potentially_responsible_party || responsibleParty;
  const confScore = assessment?.responsibility_confidence || confidence;

  const supportingEvidence = assessment?.evidence_supporting_assessment || [
    "Earliest recorded breach (4.2G shock pulse + +12.4°C thermal excursion) detected at 17:15 UTC.",
    "Breach occurred exactly +2h 45m post-origin interchange.",
    "Origin custody transfer documented at 14:30 UTC at APM Terminals Pier 400.",
    "Exclusive Care, Custody & Control held by Apex Drayage Logistics LLC at exact time of breach.",
    "Signed EIR Gate Receipt #9842 noted 'CLEAN' condition without defect exceptions at origin."
  ];

  const conflictingEvidence = assessment?.conflicting_evidence || [
    "Carrier driver verbally alleged unit was warm prior to outgate; however, driver signed clean interchange receipt without noting exception, legally waiving pre-existing defect defenses."
  ];

  const uncertainties = assessment?.uncertainties || [
    "Refrigeration pre-cooling logs at shipper facility verified nominal, but exact compressor failure mode (mechanical vs impact-induced) requires physical inspection."
  ];

  const frameworks = assessment?.applicable_legal_framework || [
    {
      framework_name: "Carmack Amendment (49 U.S.C. § 14706)",
      key_legal_principle: "Establishes strict prima facie liability on motor carriers for loss/damage during transit upon proof of delivery in good condition at origin and damage at destination."
    },
    {
      framework_name: "Uniform Intermodal Interchange Agreement (UIIA Section E.2)",
      key_legal_principle: "Motor carrier assumes full Care, Custody, and Control upon signing gate interchange receipt at terminal."
    }
  ];

  const recommendedAction = assessment?.recommended_recovery_action || 
    "Issue formal Subrogation Demand Letter to Apex Drayage Claims Dept for full claimed loss under 49 U.S.C. § 14706.";

  return (
    <div className="glass-card p-8 space-y-8 shadow-sm">
      {/* Document Header */}
      <div className="border-b-2 border-slate-900 pb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Bot className="w-6 h-6 text-blue-700" />
          <h2 className="text-2xl font-black text-slate-900 tracking-tight uppercase">
            Evidence-Backed Responsibility Assessment
          </h2>
        </div>
        <div className="flex items-center gap-2 px-3 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded text-xs font-bold uppercase tracking-widest">
          <CheckCircle2 className="w-3.5 h-3.5" />
          Evidence Grounded
        </div>
      </div>

      <div className="space-y-8 text-sm">
        
        {/* Potentially Responsible Party */}
        <section className="space-y-2">
          <h3 className="text-sm font-bold text-slate-500 uppercase tracking-widest border-b border-slate-200 pb-1 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-blue-600" />
            Potentially Responsible Party
          </h3>
          <p className="text-lg font-black text-slate-900 px-2 border-l-4 border-blue-600 bg-blue-50/50 py-2">
            {partyName}
          </p>
        </section>

        {/* Confidence */}
        <section className="space-y-2">
          <h3 className="text-sm font-bold text-slate-500 uppercase tracking-widest border-b border-slate-200 pb-1 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            Confidence
          </h3>
          <div className="flex items-center gap-4 px-2">
            <span className="text-2xl font-black text-emerald-600">{Math.round(confScore * 100)}%</span>
            <div className="flex-1 max-w-xs bg-slate-100 h-2 rounded-full overflow-hidden">
              <div className="bg-emerald-500 h-full rounded-full" style={{ width: `${Math.round(confScore * 100)}%` }} />
            </div>
          </div>
        </section>

        {/* Supporting Evidence */}
        <section className="space-y-2">
          <h3 className="text-sm font-bold text-slate-500 uppercase tracking-widest border-b border-slate-200 pb-1">
            Supporting Evidence
          </h3>
          <ul className="space-y-2 px-2">
            {supportingEvidence.map((ev: string, idx: number) => (
              <li key={idx} className="flex items-start gap-2 text-slate-700">
                <ChevronRight className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
                <span className="leading-relaxed font-medium">{ev}</span>
              </li>
            ))}
          </ul>
        </section>

        {/* Conflicting Evidence */}
        {conflictingEvidence && conflictingEvidence.length > 0 && (
          <section className="space-y-2">
            <h3 className="text-sm font-bold text-slate-500 uppercase tracking-widest border-b border-slate-200 pb-1 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              Conflicting Evidence
            </h3>
            <ul className="space-y-2 px-2">
              {conflictingEvidence.map((ev: string, idx: number) => (
                <li key={idx} className="flex items-start gap-2 text-slate-700">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0 mt-2" />
                  <span className="leading-relaxed bg-amber-50/50 p-2 rounded border border-amber-100">{ev}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Uncertainty */}
        {uncertainties && uncertainties.length > 0 && (
          <section className="space-y-2">
            <h3 className="text-sm font-bold text-slate-500 uppercase tracking-widest border-b border-slate-200 pb-1 flex items-center gap-2">
              <HelpCircle className="w-4 h-4 text-cyan-600" />
              Uncertainty
            </h3>
            <ul className="space-y-2 px-2">
              {uncertainties.map((unc: string, idx: number) => (
                <li key={idx} className="flex items-start gap-2 text-slate-700">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 shrink-0 mt-2" />
                  <span className="leading-relaxed">{unc}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Applicable Framework / Reference */}
        <section className="space-y-3">
          <h3 className="text-sm font-bold text-slate-500 uppercase tracking-widest border-b border-slate-200 pb-1 flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-slate-600" />
            Applicable Framework / Reference
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 px-2">
            {frameworks.map((fw: any, idx: number) => (
              <div key={idx} className="bg-slate-50 border border-slate-200 p-3 rounded space-y-1">
                <h4 className="font-bold text-slate-900 text-xs">{fw.framework_name}</h4>
                <p className="text-slate-600 text-xs leading-relaxed">{fw.key_legal_principle}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Recommended Next Action */}
        <section className="space-y-2">
          <h3 className="text-sm font-bold text-slate-500 uppercase tracking-widest border-b border-slate-200 pb-1 flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-emerald-600" />
            Recommended Next Action
          </h3>
          <div className="px-2 py-3 bg-emerald-50 border border-emerald-200 rounded font-bold text-emerald-900 leading-relaxed shadow-xs">
            {recommendedAction}
          </div>
        </section>

      </div>
    </div>
  );
};
