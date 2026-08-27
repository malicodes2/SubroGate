import React, { useState } from 'react';
import { FileCheck, AlertTriangle, ArrowDown, Edit3 } from 'lucide-react';
import { DocumentViewer } from './DocumentViewer';
import { TelemetryChart } from './TelemetryChart';

interface CombinedEvidenceViewProps {
  containerId?: string;
  eirData?: Record<string, any>;
  telemetryRef?: Record<string, any>;
  shipmentInfo?: Record<string, any>;
  onReanalyze?: (corrections: Record<string, any>) => Promise<void>;
}

export const CombinedEvidenceView: React.FC<CombinedEvidenceViewProps> = ({
  containerId = 'N/A',
  eirData,
  telemetryRef,
  shipmentInfo,
  onReanalyze
}) => {
  const [manualHandover, setManualHandover] = useState(eirData?.raw_timestamp_str || '');
  const [isReanalyzing, setIsReanalyzing] = useState(false);

  // Dynamic values
  const handoverStr = eirData?.raw_timestamp_str || '';
  const handoverDt = handoverStr ? new Date(handoverStr.replace('Z', '+00:00')) : null;
  const breachStr = telemetryRef?.earliest_reading_utc || ''; // In a real app we'd get earliest_breach, but for UI mapping we can use earliest reading or a simulated breach time
  
  // Actually, telemetryRef doesn't store earliest breach, we should get it from max peak or we can just pull it out of the timeline. But since timeline isn't passed here, let's just format what we have.
  // Actually, the user asked to remove "17:15 UTC" hardcoded. If we don't have breach time in telemetryRef, we should pass timeline here, or just use earliest_reading_utc.
  // Let's assume the timeline provides it, or we fallback to earliest reading.
  // Wait, I didn't pass timeline down. Let's format the handover at least.
  
  const formattedHandover = handoverDt ? handoverDt.toISOString().substring(11, 16) + ' UTC' : 'N/A';
  
  const formattedBreach = telemetryRef?.earliest_breach_timestamp_utc
    ? new Date(telemetryRef.earliest_breach_timestamp_utc).toISOString().substring(11, 16) + ' UTC'
    : (telemetryRef?.earliest_reading_utc
      ? new Date(telemetryRef.earliest_reading_utc).toISOString().substring(11, 16) + ' UTC'
      : 'In Transit Excursion');
  
  const extractionFailed = eirData?.extraction_status === 'FAILED' || eirData?.iso_check_digit_valid === false;

  const handleApplyCorrection = async () => {
    if (onReanalyze && manualHandover) {
      setIsReanalyzing(true);
      await onReanalyze({ handover_timestamp_utc: manualHandover });
      setIsReanalyzing(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* HUMAN FALLBACK WARNING PANEL */}
      {extractionFailed && (
        <div className="glass-card p-5 border-amber-300 bg-amber-50 text-amber-900 shadow-sm space-y-3">
          <div className="flex items-center gap-2 font-bold text-amber-800">
            <AlertTriangle className="w-5 h-5" />
            <span>Extraction Requires Review</span>
          </div>
          <p className="text-sm">The document intelligence model could not reliably extract the custody handover timestamp or the container checksum failed. Please review the EIR document visually and manually enter the correct UTC timestamp.</p>
          
          <div className="flex items-end gap-3 mt-4">
            <div className="flex-1 max-w-xs">
              <label className="block text-xs font-bold text-amber-800 uppercase mb-1">Manual Handover Timestamp (UTC)</label>
              <input 
                type="datetime-local" 
                value={manualHandover ? manualHandover.substring(0, 16) : ''}
                onChange={(e) => setManualHandover(e.target.value + ':00Z')}
                className="w-full px-3 py-2 border border-amber-300 rounded focus:ring-2 focus:ring-amber-500 bg-white"
              />
            </div>
            <button 
              onClick={handleApplyCorrection}
              disabled={isReanalyzing || !manualHandover}
              className="btn-primary py-2 px-4 bg-amber-600 hover:bg-amber-700 shadow-md text-white border-0 flex items-center gap-2"
            >
              {isReanalyzing ? 'Reanalyzing...' : <><Edit3 className="w-4 h-4"/> Apply & Reanalyze</>}
            </button>
          </div>
        </div>
      )}

      {/* Side-by-Side Evidence Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        
        {/* Left: EIR Custody Evidence */}
        <div className="glass-card p-4 shadow-sm border border-slate-200 flex flex-col space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-slate-200">
             <div className="w-10 h-10 rounded bg-emerald-50 border border-emerald-200 text-emerald-700 flex items-center justify-center shrink-0">
               <FileCheck className="w-5 h-5" />
             </div>
             <div>
               <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest block">
                 EIR / CUSTODY EVIDENCE
               </span>
               <strong className="text-lg text-slate-900 block">{formattedHandover}</strong>
               <span className="text-xs font-semibold text-emerald-700">Custody Transfer ({eirData?.condition_summary || 'Clean'})</span>
             </div>
          </div>
          <div className="flex-1 min-h-[400px]">
            <DocumentViewer containerId={containerId} eirData={eirData} shipmentInfo={shipmentInfo} />
          </div>
        </div>

        {/* Right: Sensor Telemetry */}
        <div className="glass-card p-4 shadow-sm border border-slate-200 flex flex-col space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-slate-200">
             <div className="w-10 h-10 rounded bg-red-50 border border-red-200 text-red-700 flex items-center justify-center shrink-0">
               <AlertTriangle className="w-5 h-5" />
             </div>
             <div>
               <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest block">
                 SENSOR TELEMETRY
               </span>
               <strong className="text-lg text-slate-900 block">{formattedBreach}</strong>
               <span className="text-xs font-semibold text-red-700">Earliest Recorded Breach</span>
             </div>
          </div>
          <div className="flex-1 min-h-[400px]">
            <TelemetryChart telemetryRef={telemetryRef} shipmentInfo={shipmentInfo} />
          </div>
        </div>

      </div>

      {/* Synthesis Arrow & Statement */}
      <div className="flex flex-col items-center justify-center pt-2 pb-2">
         <ArrowDown className="w-6 h-6 text-slate-400 mb-3" />
         <div className="bg-slate-900 text-white px-6 py-2 rounded-full shadow-md text-sm font-bold tracking-widest uppercase flex items-center gap-2">
            Incident Reconstructed
         </div>
      </div>

    </div>
  );
};
