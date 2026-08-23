import React from 'react';
import { FileCheck, AlertTriangle, ArrowDown } from 'lucide-react';
import { DocumentViewer } from './DocumentViewer';
import { TelemetryChart } from './TelemetryChart';

interface CombinedEvidenceViewProps {
  containerId?: string;
  eirData?: Record<string, any>;
  telemetryRef?: Record<string, any>;
}

export const CombinedEvidenceView: React.FC<CombinedEvidenceViewProps> = ({
  containerId = 'N/A',
  eirData,
  telemetryRef
}) => {
  return (
    <div className="space-y-6">
      
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
               <strong className="text-lg text-slate-900 block">14:30 UTC</strong>
               <span className="text-xs font-semibold text-emerald-700">Custody Transfer (Clean)</span>
             </div>
          </div>
          <div className="flex-1 min-h-[400px]">
            <DocumentViewer containerId={containerId} eirData={eirData} />
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
               <strong className="text-lg text-slate-900 block">17:15 UTC</strong>
               <span className="text-xs font-semibold text-red-700">Earliest Recorded Breach</span>
             </div>
          </div>
          <div className="flex-1 min-h-[400px]">
            <TelemetryChart telemetryRef={telemetryRef} />
          </div>
        </div>

      </div>

      {/* Synthesis Arrow & Statement */}
      <div className="flex flex-col items-center justify-center pt-2 pb-2">
         <ArrowDown className="w-6 h-6 text-slate-400 mb-3" />
         <div className="bg-slate-900 text-white px-6 py-2 rounded-full shadow-md text-sm font-bold tracking-widest uppercase flex items-center gap-2">
            Incident Reconstructed
         </div>
         <p className="text-sm text-slate-600 font-medium mt-3 text-center max-w-lg">
           Recorded breach occurred <strong className="text-slate-900">2h 45m after</strong> physical custody transfer.
         </p>
      </div>

    </div>
  );
};
