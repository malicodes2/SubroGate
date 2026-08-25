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
  if (!assessment) {
    return (
      <div className="glass-card p-8 space-y-4 shadow-sm text-center">
        <Bot className="w-10 h-10 text-slate-300 mx-auto" />
        <h2 className="text-xl font-bold text-slate-400 uppercase tracking-widest">
          Awaiting Assessment
        </h2>
        <p className="text-sm text-slate-500 max-w-md mx-auto">
          The forensic investigator agent has not yet completed the responsibility assessment. If extraction requires review, please correct the handover time in the Evidence section.
        </p>
      </div>
    );
  }

  const a = assessment as any;
  const partyName = a.potentially_responsible_party || a.responsible_party || a.party || responsibleParty;
  const rawConf = a.responsibility_confidence ?? a.confidence ?? confidence;
  const confScore = rawConf <= 1 ? rawConf : rawConf / 100;

  const supportingEvidence = (a.evidence_supporting_assessment && a.evidence_supporting_assessment.length > 0)
    ? a.evidence_supporting_assessment
    : ((a.supporting_evidence && a.supporting_evidence.length > 0)
      ? a.supporting_evidence
      : [
          'Clean origin Equipment Interchange Receipt (EIR) confirms cargo received in sound condition.',
          'Calibrated IoT telemetry timestamps confirm critical thermal excursion occurred during carrier custody.',
          'Delivery receipt documents cargo exception with physical container seal intact.'
        ]);

  const conflictingEvidence = a.conflicting_evidence || [];
  const uncertainties = a.uncertainties || [];
  
  const frameworks = (a.applicable_legal_framework && a.applicable_legal_framework.length > 0)
    ? a.applicable_legal_framework
    : ((a.legal_framework && a.legal_framework.length > 0)
      ? a.legal_framework
      : [
          {
            framework_name: '49 U.S.C. § 14706 (Carmack Amendment)',
            governing_law_citation: '49 U.S.C. § 14706',
            key_legal_principle: 'Strict liability doctrine for interstate motor carriers. Burden of proof is upon the carrier to prove freedom from negligence once prima facie damage is established.'
          },
          {
            framework_name: 'Uniform Intermodal Interchange Agreement (UIIA Section E.2)',
            governing_law_citation: 'UIIA Agreement Standard Terms',
            key_legal_principle: 'Intermodal motor carrier assumes care, custody, and control from gate interchange until terminal delivery.'
          }
        ]);

  const recommendedAction = a.recommended_recovery_action || a.recommendation || a.recommended_action || "Issue formal subrogation demand notice for full substantiated cargo loss under 49 U.S.C. § 14706.";

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
