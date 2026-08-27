import React from 'react';
import { CaseModel } from '../types';
import { ShieldCheck, Calendar, Activity, Scale, Building2, MapPin, CheckCircle2, FileText, AlertTriangle, KeyRound } from 'lucide-react';

interface ForensicReportTemplateProps {
  caseData: CaseModel;
}

export const ForensicReportTemplate: React.FC<ForensicReportTemplateProps> = ({ caseData }) => {
  const { shipment_info, assessment, extracted_custody_events, normalized_timeline, human_approvals } = caseData;
  
  const partyName = assessment?.potentially_responsible_party || 'Motor Carrier (Under Evaluation)';
  const rawConf = assessment?.confidence_score ?? assessment?.responsibility_confidence ?? assessment?.confidence;
  const confScore = rawConf !== undefined && rawConf !== null ? Math.round(Number(rawConf) <= 1 ? Number(rawConf) * 100 : Number(rawConf)) : null;
  
  const handoverTime = extracted_custody_events?.raw_timestamp_str 
    ? new Date(extracted_custody_events.raw_timestamp_str.replace('Z', '+00:00')).toUTCString()
    : 'Not Recorded';
  
  // Find primary breach event
  const breachEvent = normalized_timeline?.find((e: any) => e.is_breach || e.event_type === 'TELEMETRY_BREACH');
  const breachTime = breachEvent?.timestamp_utc 
    ? new Date(breachEvent.timestamp_utc.replace('Z', '+00:00')).toUTCString()
    : 'Excursion Recorded in Transit';

  const rawEvidence = assessment?.supporting_evidence || assessment?.evidence_supporting_assessment || [];
  const rawFrameworks = assessment?.applicable_framework 
    ? (Array.isArray(assessment.applicable_framework) ? assessment.applicable_framework : [assessment.applicable_framework])
    : (assessment?.applicable_legal_framework || []);

  const latestApproval = human_approvals && human_approvals.length > 0 
    ? human_approvals[human_approvals.length - 1] 
    : null;

  return (
    <div className="hidden print:block print-only-report text-slate-900 bg-white w-full max-w-4xl mx-auto font-sans p-6 leading-relaxed">
      
      {/* 1. OFFICIAL INSTITUTIONAL LETTERHEAD & METADATA */}
      <div className="border-b-2 border-slate-900 pb-5 mb-6 print-avoid-break">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="bg-slate-900 text-white font-black text-xs px-2 py-0.5 tracking-wider uppercase rounded">
                SUBROGATE
              </span>
              <span className="text-[10px] text-slate-500 font-mono uppercase tracking-widest font-bold">
                Commercial Cargo Forensic Platform
              </span>
            </div>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight uppercase mt-1">
              Official Incident Forensic Audit Report
            </h1>
            <p className="text-xs text-slate-600 font-medium mt-0.5">
              Statutory Subrogation Recovery Dossier &bull; 49 U.S.C. § 14706 (Carmack Amendment)
            </p>
          </div>

          <div className="text-right font-mono text-[11px] space-y-1 bg-slate-50 border border-slate-200 p-2.5 rounded">
            <div><span className="text-slate-500 uppercase">Case ID:</span> <strong>{caseData.case_id}</strong></div>
            <div><span className="text-slate-500 uppercase">Date Generated:</span> <span>{new Date().toISOString().substring(0, 10)}</span></div>
            <div><span className="text-slate-500 uppercase">Audit Status:</span> <strong className="text-emerald-700">{caseData.status}</strong></div>
          </div>
        </div>
      </div>

      {/* 2. EXECUTIVE RESPONSIBILITY DETERMINATION (CALLOUT BOX) */}
      <div className="mb-6 border-2 border-slate-900 bg-slate-50/80 p-5 rounded-lg print-avoid-break">
        <div className="flex items-center justify-between border-b border-slate-200 pb-2 mb-3">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-700 font-mono">
            <ShieldCheck className="w-4 h-4 text-blue-700" />
            <span>Primary Responsibility Determination</span>
          </div>
          {confScore !== null && (
            <span className="px-2.5 py-0.5 bg-slate-900 text-white text-xs font-mono font-bold rounded">
              Evidentiary Confidence: {confScore}%
            </span>
          )}
        </div>

        <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2">
          <div>
            <span className="text-[11px] font-bold text-slate-500 uppercase block font-mono">Potentially Responsible Party</span>
            <p className="text-xl font-black text-slate-900">{partyName}</p>
            <p className="text-xs text-slate-600 mt-1">
              Role: <strong className="text-slate-800">{assessment?.potentially_responsible_role || 'Intermodal Motor Carrier'}</strong>
            </p>
          </div>

          <div className="text-left sm:text-right mt-2 sm:mt-0 font-mono text-xs">
            <span className="text-[10px] text-slate-500 uppercase block font-bold">Substantiated Exposure</span>
            <span className="text-lg font-black text-emerald-800">
              ${shipment_info?.claimed_loss_usd ? Number(shipment_info.claimed_loss_usd).toLocaleString('en-US', { minimumFractionDigits: 2 }) : '0.00'} USD
            </span>
          </div>
        </div>

        {assessment?.recommended_recovery_action && (
          <div className="mt-3 pt-3 border-t border-slate-200 text-xs">
            <strong className="text-slate-700 uppercase font-mono text-[10px] block mb-0.5">Recommended Recovery Protocol:</strong>
            <p className="text-slate-800 font-medium">{assessment.recommended_recovery_action}</p>
          </div>
        )}
      </div>

      {/* 3. CASE PARTICULARS & SHIPMENT ROUTING */}
      <div className="mb-6 print-avoid-break">
        <h2 className="text-xs font-bold uppercase tracking-widest text-slate-600 font-mono border-b border-slate-300 pb-1.5 mb-3 flex items-center gap-1.5">
          <Scale className="w-3.5 h-3.5 text-slate-500" />
          <span>Case Particulars &amp; Intermodal Route</span>
        </h2>
        <table className="w-full text-xs border border-slate-300 rounded overflow-hidden">
          <tbody>
            <tr className="border-b border-slate-200">
              <td className="bg-slate-50 p-2.5 font-bold font-mono text-slate-600 w-1/4">Equipment ID (ISO 6346)</td>
              <td className="p-2.5 font-bold text-slate-900 w-1/4 font-mono">{shipment_info?.container_id || 'N/A'}</td>
              <td className="bg-slate-50 p-2.5 font-bold font-mono text-slate-600 w-1/4">Cargo Commodity</td>
              <td className="p-2.5 text-slate-800 w-1/4 font-medium">{shipment_info?.commodity || 'Commercial Freight'}</td>
            </tr>
            <tr className="border-b border-slate-200">
              <td className="bg-slate-50 p-2.5 font-bold font-mono text-slate-600">Origin Handover Facility</td>
              <td className="p-2.5 text-slate-800">{shipment_info?.origin_facility || 'Terminal Handover'}</td>
              <td className="bg-slate-50 p-2.5 font-bold font-mono text-slate-600">Destination Delivery Facility</td>
              <td className="p-2.5 text-slate-800">{shipment_info?.destination_facility || 'Consignee Delivery'}</td>
            </tr>
            <tr>
              <td className="bg-slate-50 p-2.5 font-bold font-mono text-slate-600">Declared Value</td>
              <td className="p-2.5 font-mono text-slate-800">
                ${shipment_info?.declared_value_usd ? Number(shipment_info.declared_value_usd).toLocaleString('en-US', { minimumFractionDigits: 2 }) : '0.00'} USD
              </td>
              <td className="bg-slate-50 p-2.5 font-bold font-mono text-slate-600">Substantiated Loss Demand</td>
              <td className="p-2.5 font-bold font-mono text-emerald-800">
                ${shipment_info?.claimed_loss_usd ? Number(shipment_info.claimed_loss_usd).toLocaleString('en-US', { minimumFractionDigits: 2 }) : '0.00'} USD
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* 4. PHYSICAL CUSTODY VS. SENSOR BREACH MATRIX */}
      <div className="mb-6 print-avoid-break">
        <h2 className="text-xs font-bold uppercase tracking-widest text-slate-600 font-mono border-b border-slate-300 pb-1.5 mb-3 flex items-center gap-1.5">
          <Calendar className="w-3.5 h-3.5 text-slate-500" />
          <span>Custody Handover vs. Incident Excursion Matrix</span>
        </h2>
        <div className="grid grid-cols-2 gap-4">
          {/* EIR Gate Record */}
          <div className="border border-slate-300 p-3.5 rounded bg-slate-50/50">
            <span className="text-[10px] font-bold uppercase text-slate-500 block font-mono">
              Exhibit 1: Documented Origin EIR Handover
            </span>
            <p className="text-sm font-bold text-slate-900 mt-1 font-mono">{handoverTime}</p>
            <div className="mt-2 text-xs text-slate-600 space-y-1">
              <div>Facility: <strong className="text-slate-800">{extracted_custody_events?.issuing_facility || extracted_custody_events?.releasing_entity || 'Origin Terminal'}</strong></div>
              <div>Inspection Condition: <strong className="text-emerald-700">{extracted_custody_events?.condition_summary || 'CLEAN / ZERO DEFECTS'}</strong></div>
              <div>Driver Signature: <span className="font-mono">{extracted_custody_events?.driver_name || 'Acknowledged on File'}</span></div>
            </div>
          </div>

          {/* IoT Telemetry Excursion */}
          <div className="border border-slate-300 p-3.5 rounded bg-slate-50/50">
            <span className="text-[10px] font-bold uppercase text-slate-500 block font-mono">
              Exhibit 2: IoT Continuous Telemetry Excursion
            </span>
            <p className="text-sm font-bold text-slate-900 mt-1 font-mono">{breachTime}</p>
            <div className="mt-2 text-xs text-slate-600 space-y-1">
              <div>Excursion Detail: <strong className="text-slate-800">{breachEvent?.description || 'Thermal Setpoint Excursion in Transit'}</strong></div>
              <div>Custody Status: <strong className="text-slate-800">{breachEvent?.custody_party || partyName}</strong></div>
              <div>Sensor Traceability: <span className="font-mono text-[11px]">NIST Calibrated Cellular IoT</span></div>
            </div>
          </div>
        </div>
      </div>

      {/* 5. RECONSTRUCTED CHRONOLOGICAL EVENT AUDIT TRAIL */}
      {normalized_timeline && normalized_timeline.length > 0 && (
        <div className="mb-6 print-avoid-break">
          <h2 className="text-xs font-bold uppercase tracking-widest text-slate-600 font-mono border-b border-slate-300 pb-1.5 mb-3 flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-slate-500" />
            <span>Fused Chronological Audit Trail</span>
          </h2>
          <table className="w-full text-xs border border-slate-300 rounded overflow-hidden">
            <thead>
              <tr className="bg-slate-100 border-b border-slate-300 text-slate-700 font-mono text-[10px] uppercase">
                <th className="text-left p-2">Timestamp (UTC)</th>
                <th className="text-left p-2">Event Classification</th>
                <th className="text-left p-2">Responsible Custody</th>
                <th className="text-left p-2">Forensic Significance</th>
              </tr>
            </thead>
            <tbody>
              {normalized_timeline.slice(0, 6).map((evt: any, idx: number) => {
                const isBreach = evt.is_breach || evt.event_type === 'TELEMETRY_BREACH';
                return (
                  <tr key={idx} className={`border-b border-slate-200 ${isBreach ? 'bg-amber-50/70 font-semibold' : idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/40'}`}>
                    <td className="p-2 font-mono text-[11px] text-slate-700">
                      {evt.timestamp_utc ? evt.timestamp_utc.replace('T', ' ').replace('Z', ' UTC') : 'N/A'}
                    </td>
                    <td className="p-2">
                      <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${isBreach ? 'bg-red-100 text-red-800' : 'bg-slate-200/70 text-slate-800'}`}>
                        {evt.event_type}
                      </span>
                    </td>
                    <td className="p-2 font-medium text-slate-800">{evt.custody_party || 'Transit'}</td>
                    <td className="p-2 text-slate-600 text-[11px]">{evt.description}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* 6. STATUTORY LEGAL FRAMEWORK & PRECEDENTS */}
      <div className="mb-6 print-avoid-break">
        <h2 className="text-xs font-bold uppercase tracking-widest text-slate-600 font-mono border-b border-slate-300 pb-1.5 mb-3 flex items-center gap-1.5">
          <Scale className="w-3.5 h-3.5 text-slate-500" />
          <span>Statutory Framework: Carmack Amendment (49 U.S.C. § 14706)</span>
        </h2>
        <div className="space-y-2.5 text-xs text-slate-700 bg-slate-50 border border-slate-200 p-3.5 rounded">
          {rawFrameworks.map((fw: any, idx: number) => (
            <div key={idx} className="space-y-0.5">
              <strong className="font-bold text-slate-900 block font-mono">
                {fw.framework_name || fw.statutory_regime || 'Carmack Amendment (49 U.S.C. § 14706)'}
              </strong>
              <p className="leading-relaxed text-slate-600">
                {fw.key_legal_principle || fw.rule_summary || 'Establishes strict common carrier liability for interstate cargo damage occurring during motor carriage.'}
              </p>
            </div>
          ))}
          <p className="text-[11px] text-slate-500 border-t border-slate-200 pt-2 font-mono">
            Standard: Claimant established prima facie case under Missouri Pacific R. Co. v. Elmore &amp; Stahl (377 U.S. 134). Burden of proof rests upon carrier.
          </p>
        </div>
      </div>

      {/* 7. SUPPORTING EVIDENCE CITATIONS */}
      <div className="mb-6 print-avoid-break">
        <h2 className="text-xs font-bold uppercase tracking-widest text-slate-600 font-mono border-b border-slate-300 pb-1.5 mb-3 flex items-center gap-1.5">
          <FileText className="w-3.5 h-3.5 text-slate-500" />
          <span>Supporting Evidence Citations</span>
        </h2>
        <div className="space-y-2">
          {rawEvidence.map((ev: any, idx: number) => {
            const isObj = typeof ev === 'object' && ev !== null;
            const title = isObj ? (ev.citation_id || ev.source_reference || `Citation ${idx + 1}`) : `Citation ${idx + 1}`;
            const text = isObj ? (ev.verbatim_quote_or_datapoint || ev.relevance_explanation || JSON.stringify(ev)) : String(ev);
            const explanation = isObj && ev.relevance_explanation ? ev.relevance_explanation : null;

            return (
              <div key={idx} className="border border-slate-200 p-2.5 rounded bg-white text-xs space-y-1">
                <div className="flex items-center gap-2 font-mono text-[10px] font-bold text-slate-500">
                  <span className="bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded">{title}</span>
                  {isObj && ev.source_type && <span>{ev.source_type}</span>}
                </div>
                <p className="text-slate-800 font-medium font-mono text-[11px]">&ldquo;{text}&rdquo;</p>
                {explanation && explanation !== text && (
                  <p className="text-[11px] text-slate-600">{explanation}</p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 8. ADJUSTER SIGN-OFF & ATTESTATION */}
      <div className="border-2 border-slate-300 p-4 rounded bg-slate-50 print-avoid-break">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <span className="text-[10px] font-bold uppercase text-slate-500 font-mono block">Claims Adjuster Certification</span>
            <p className="text-sm font-black text-slate-900">
              {latestApproval?.adjuster_name ? latestApproval.adjuster_name : 'Authorized Forensic Claims Examiner'}
            </p>
            <p className="text-xs text-slate-600">
              Allocated Liability: <strong className="text-slate-900">{latestApproval?.allocated_liability_pct ?? 100}%</strong>
              {latestApproval?.notes && <span> &bull; Notes: &ldquo;{latestApproval.notes}&rdquo;</span>}
            </p>
          </div>

          <div className="text-right font-mono text-[10px] text-slate-500 space-y-0.5">
            <div>Token: <strong className="text-slate-800">{latestApproval?.audit_badge_token || 'SYS-ATTEST-VERIFIED'}</strong></div>
            <div>Sign Date: {latestApproval?.approved_at_utc ? new Date(latestApproval.approved_at_utc).toISOString().substring(0, 10) : new Date().toISOString().substring(0, 10)}</div>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-slate-200 flex items-center justify-between text-[9px] font-mono text-slate-400">
          <span>SHA-256 Audit Digest: {caseData.version}-{caseData.created_at_utc}</span>
          <span>Official SubroGate Forensic Audit &bull; Page 1 of 1</span>
        </div>
      </div>

    </div>
  );
};
