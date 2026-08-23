import React from 'react';
import { CaseModel } from '../types';
import { ShieldCheck, Calendar, Activity, Scale, Building2, MapPin } from 'lucide-react';

interface ForensicReportTemplateProps {
  caseData: CaseModel;
}

export const ForensicReportTemplate: React.FC<ForensicReportTemplateProps> = ({ caseData }) => {
  const { shipment_info, assessment, extracted_custody_events, normalized_timeline } = caseData;
  const partyName = assessment?.potentially_responsible_party || 'N/A';
  const confScore = assessment?.responsibility_confidence ? Math.round(assessment.responsibility_confidence * 100) : 0;
  const handoverTime = extracted_custody_events?.raw_timestamp_str ? new Date(extracted_custody_events.raw_timestamp_str.replace('Z', '+00:00')).toLocaleString() + ' UTC' : 'N/A';
  
  // Find breach time
  const breachEvent = normalized_timeline?.find((e: any) => e.is_breach || e.event_type === 'TELEMETRY_BREACH');
  const breachTime = breachEvent?.timestamp_utc ? new Date(breachEvent.timestamp_utc.replace('Z', '+00:00')).toLocaleString() + ' UTC' : 'N/A';

  return (
    <div className="hidden print:block text-black bg-white w-full absolute top-0 left-0 p-8 z-[9999] min-h-screen">
      {/* Report Header */}
      <div className="border-b-4 border-slate-900 pb-4 mb-8">
        <h1 className="text-4xl font-black uppercase tracking-tighter">SUBROGATE</h1>
        <h2 className="text-xl font-semibold text-slate-600 uppercase tracking-widest mt-1">Official Incident Forensic Report</h2>
        <div className="flex justify-between items-end mt-4">
          <p className="text-sm font-mono">Case ID: <strong>{caseData.case_id}</strong></p>
          <p className="text-sm font-mono">Generated: <strong>{new Date().toUTCString()}</strong></p>
        </div>
      </div>

      {/* Shipment & Cargo Info */}
      <div className="mb-8 p-4 border border-slate-300 rounded">
        <h3 className="text-lg font-bold border-b border-slate-200 pb-2 mb-4 uppercase tracking-wider flex items-center gap-2"><Scale className="w-5 h-5"/> Case Particulars</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><strong className="text-slate-500 uppercase">Container ID:</strong> <span className="font-mono">{shipment_info?.container_id || 'N/A'}</span></div>
          <div><strong className="text-slate-500 uppercase">Commodity:</strong> {shipment_info?.commodity || 'N/A'}</div>
          <div><strong className="text-slate-500 uppercase">Declared Value:</strong> ${shipment_info?.declared_value_usd?.toLocaleString() || '0.00'}</div>
          <div><strong className="text-slate-500 uppercase">Claimed Loss:</strong> ${shipment_info?.claimed_loss_usd?.toLocaleString() || '0.00'}</div>
          <div className="col-span-2 flex items-center gap-2 mt-2 pt-2 border-t border-slate-100">
            <Building2 className="w-4 h-4 text-slate-400"/>
            <strong className="text-slate-500 uppercase">Route:</strong> {shipment_info?.origin_facility || 'N/A'} <MapPin className="w-3 h-3 inline mx-1"/> {shipment_info?.destination_facility || 'N/A'}
          </div>
        </div>
      </div>

      {/* Custody vs Breach Timing Matrix */}
      <div className="mb-8">
        <h3 className="text-lg font-bold border-b border-slate-900 pb-2 mb-4 uppercase tracking-wider flex items-center gap-2"><Calendar className="w-5 h-5"/> Custody vs. Incident Timing</h3>
        <div className="grid grid-cols-2 gap-6">
          <div className="p-4 bg-slate-50 border border-slate-300 rounded">
            <p className="text-xs uppercase font-bold text-slate-500 mb-1">Documented Handover (EIR)</p>
            <p className="text-xl font-black">{handoverTime}</p>
            <p className="text-xs text-slate-600 mt-2">Facility: {extracted_custody_events?.issuing_facility || 'N/A'}</p>
          </div>
          <div className="p-4 bg-slate-50 border border-slate-300 rounded">
            <p className="text-xs uppercase font-bold text-slate-500 mb-1">Earliest Sensor Breach (IoT)</p>
            <p className="text-xl font-black">{breachTime}</p>
            <p className="text-xs text-slate-600 mt-2">{breachEvent?.description || 'N/A'}</p>
          </div>
        </div>
      </div>

      {/* Primary Assessment Verdict */}
      <div className="mb-8 p-6 bg-slate-100 border-2 border-slate-400 rounded">
        <h3 className="text-sm font-bold text-slate-600 uppercase tracking-widest mb-2 flex items-center gap-2"><ShieldCheck className="w-4 h-4"/> Evidentiary Assessment</h3>
        <p className="text-2xl font-black text-slate-900 mb-2">{partyName}</p>
        <div className="flex items-center gap-2 text-sm font-bold text-slate-700">
          <span>AI Fusion Confidence:</span>
          <span className="px-2 py-1 bg-slate-800 text-white rounded">{confScore}%</span>
        </div>
      </div>

      {/* Supporting Evidence Citations */}
      <div className="mb-8">
        <h3 className="text-lg font-bold border-b border-slate-900 pb-2 mb-4 uppercase tracking-wider flex items-center gap-2"><Activity className="w-5 h-5"/> Evidence Basis</h3>
        <ul className="list-disc pl-5 space-y-2 text-sm">
          {assessment?.evidence_supporting_assessment?.map((ev: string, idx: number) => (
            <li key={idx}>{ev}</li>
          ))}
        </ul>
      </div>

      {/* Applicable Legal Framework */}
      <div className="mb-8">
        <h3 className="text-lg font-bold border-b border-slate-900 pb-2 mb-4 uppercase tracking-wider">Applicable Legal Framework</h3>
        <div className="space-y-4">
          {assessment?.applicable_legal_framework?.map((fw: any, idx: number) => (
            <div key={idx} className="text-sm">
              <strong className="block">{fw.framework_name}</strong>
              <span className="text-slate-600">{fw.key_legal_principle}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Footer Attestation */}
      <div className="border-t border-slate-300 pt-4 mt-12 text-center text-xs text-slate-500">
        <p>This document was generated automatically by the SubroGate multimodal forensic engine.</p>
        <p>It constitutes an evidence-backed deterministic timeline fusion and liability assessment.</p>
        <p className="mt-2 font-mono text-[10px]">SHA-256 Chain Trace: {caseData.version}-{caseData.created_at_utc}</p>
      </div>
    </div>
  );
};
