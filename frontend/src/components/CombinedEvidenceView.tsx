import React from 'react';
import { FileCheck, AlertTriangle } from 'lucide-react';
import { DocumentViewer } from './DocumentViewer';
import { TelemetryChart } from './TelemetryChart';

interface CombinedEvidenceViewProps {
  containerId?: string;
  eirData?: Record<string, any>;
  telemetryRef?: Record<string, any>;
}

export const CombinedEvidenceView: React.FC<CombinedEvidenceViewProps> = ({
  containerId = 'MSKU9082345',
  eirData,
  telemetryRef
}) => {
  return (
    <div className="space-y-4">
      {/* Central Correlation Banner (Light Mode) */}
      <div className="glass-card p-4 border-blue-200 bg-gradient-to-r from-emerald-50/70 via-white to-red-50/70 flex flex-col md:flex-row items-center justify-between gap-4 shadow-sm">
        {/* Left Side: Handover */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-emerald-100 border border-emerald-300 flex items-center justify-center text-emerald-700 shrink-0 shadow-xs">
            <FileCheck className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] text-emerald-800 font-bold uppercase tracking-wider block">
              1. ORIGIN CUSTODY HANDOVER
            </span>
            <strong className="text-sm text-slate-900 block">14:30 UTC • APM Terminal Outgate</strong>
            <span className="text-xs text-slate-600">Clean EIR signed without pre-existing exceptions</span>
          </div>
        </div>

        {/* Center: Causal Delta Marker */}
        <div className="glass-panel px-4 py-2 text-center shrink-0 bg-white border-slate-200 shadow-xs">
          <span className="text-[10px] text-slate-500 uppercase block font-semibold">TRANSIT DELTA</span>
          <span className="text-xs font-bold text-cyan-700 block">
            +2h 45m Post-Handover
          </span>
          <span className="text-[10px] text-slate-500 block">Exclusive Carrier Care</span>
        </div>

        {/* Right Side: Breach */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-red-100 border border-red-300 flex items-center justify-center text-red-700 shrink-0 shadow-xs">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] text-red-800 font-bold uppercase tracking-wider block">
              2. EARLIEST RECORDED BREACH
            </span>
            <strong className="text-sm text-slate-900 block">17:15 UTC • In-Transit Barstow</strong>
            <span className="text-xs text-slate-600">4.2G shock pulse + thermal excursion to +12.4°C</span>
          </div>
        </div>
      </div>

      {/* Side-by-Side Synchronized Panes */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: Document */}
        <div className="h-full min-h-[500px]">
          <DocumentViewer containerId={containerId} eirData={eirData} />
        </div>

        {/* Right: Telemetry */}
        <div className="h-full min-h-[500px]">
          <TelemetryChart telemetryRef={telemetryRef} />
        </div>
      </div>
    </div>
  );
};
