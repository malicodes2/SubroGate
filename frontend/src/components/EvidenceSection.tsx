import React, { useState } from 'react';
import { Layers, FileText, Activity, Columns } from 'lucide-react';
import { DocumentViewer } from './DocumentViewer';
import { TelemetryChart } from './TelemetryChart';
import { CombinedEvidenceView } from './CombinedEvidenceView';

interface EvidenceSectionProps {
  containerId?: string;
  eirData?: Record<string, any>;
  telemetryRef?: Record<string, any>;
  onReanalyze?: (corrections: Record<string, any>) => Promise<void>;
}

export const EvidenceSection: React.FC<EvidenceSectionProps> = ({
  containerId = '',
  eirData,
  telemetryRef,
  onReanalyze
}) => {
  const [activeView, setActiveView] = useState<'combined' | 'document' | 'telemetry'>('combined');

  return (
    <div className="space-y-4">
      {/* Sleek Segmented Control Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-1">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 flex items-center justify-center shadow-xs">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Primary Evidentiary Record
            </h2>
            <p className="text-xs text-slate-500">
              Correlated physical gate receipt and continuous IoT sensor waveform
            </p>
          </div>
        </div>

        {/* Minimalist Segmented Tabs (Light Mode) */}
        <div className="flex items-center bg-slate-200/80 p-1 rounded-lg border border-slate-200 text-xs">
          <button
            onClick={() => setActiveView('combined')}
            className={`px-3 py-1.5 rounded-md transition-all flex items-center gap-1.5 ${
              activeView === 'combined'
                ? 'bg-white text-blue-700 font-bold shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Columns className="w-3.5 h-3.5" />
            <span>Combined Evidence</span>
          </button>

          <button
            onClick={() => setActiveView('document')}
            className={`px-3 py-1.5 rounded-md transition-all flex items-center gap-1.5 ${
              activeView === 'document'
                ? 'bg-white text-blue-700 font-bold shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>EIR Document</span>
          </button>

          <button
            onClick={() => setActiveView('telemetry')}
            className={`px-3 py-1.5 rounded-md transition-all flex items-center gap-1.5 ${
              activeView === 'telemetry'
                ? 'bg-white text-blue-700 font-bold shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Telemetry</span>
          </button>
        </div>
      </div>

      {/* Main Evidence Panes */}
      {activeView === 'combined' && (
        <CombinedEvidenceView
          containerId={containerId}
          eirData={eirData}
          telemetryRef={telemetryRef}
          onReanalyze={onReanalyze}
        />
      )}

      {activeView === 'document' && (
        <div className="h-[580px]">
          <DocumentViewer containerId={containerId} eirData={eirData} onReanalyze={onReanalyze} />
        </div>
      )}

      {activeView === 'telemetry' && (
        <div className="h-[520px]">
          <TelemetryChart telemetryRef={telemetryRef} />
        </div>
      )}
    </div>
  );
};
