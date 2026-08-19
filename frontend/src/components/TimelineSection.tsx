import React, { useState } from 'react';
import { Clock, ShieldAlert, MapPin, Truck, Building2, AlertTriangle, FileCheck, Info, ChevronRight } from 'lucide-react';

interface TimelineEvent {
  event_id: string;
  timestamp_utc: string;
  event_type: string;
  location_name: string;
  active_custody_holder: string;
  role: string;
  description: string;
  is_breach?: boolean;
  is_earliest_breach?: boolean;
  is_relevant_handover?: boolean;
  evidence_source?: string;
}

interface TimelineSectionProps {
  timeline: TimelineEvent[];
  responsibleParty?: string;
}

export const TimelineSection: React.FC<TimelineSectionProps> = ({
  timeline,
  responsibleParty = 'Apex Drayage Logistics LLC'
}) => {
  const [selectedEvent, setSelectedEvent] = useState<TimelineEvent | null>(
    timeline.find(e => e.is_earliest_breach) || timeline[1] || null
  );

  const formatUtcTime = (isoString?: string) => {
    if (!isoString) return '--:-- UTC';
    try {
      const dt = new Date(isoString);
      return dt.toUTCString().replace('GMT', 'UTC');
    } catch {
      return isoString;
    }
  };

  return (
    <div className="glass-card p-6 space-y-5 shadow-sm">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 flex items-center justify-center shadow-xs">
            <Clock className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Deterministic Custody &amp; Incident Timeline
            </h2>
            <p className="text-xs text-slate-500">
              UTC normalized chronological custody sequence aligning gate events with sensor stream
            </p>
          </div>
        </div>

        {/* Mathematical Proof Badge */}
        <div className="glass-panel px-3 py-1.5 rounded-lg flex items-center gap-2 text-xs bg-amber-50 border-amber-200">
          <ShieldAlert className="w-3.5 h-3.5 text-amber-600 shrink-0" />
          <span className="text-amber-900 font-bold text-[11px]">
            T_breach (17:15) &gt; T_handover (14:30)
          </span>
          <span className="text-slate-300">|</span>
          <span className="text-slate-700 text-[11px]">Exclusive Care: {responsibleParty}</span>
        </div>
      </div>

      {/* Custody Band Visualizer (Light Mode) */}
      <div className="glass-inset p-3.5 rounded-lg space-y-2 bg-slate-50 border-slate-200">
        <div className="text-xs text-slate-500 uppercase tracking-wider font-bold flex items-center justify-between">
          <span>Custody Interval Distribution</span>
          <span className="text-[11px] text-slate-400">UTC Normalized</span>
        </div>

        <div className="grid grid-cols-12 gap-1.5 h-9 rounded-md overflow-hidden p-1 bg-white border border-slate-200 text-xs shadow-xs">
          {/* APM Terminal Custody */}
          <div 
            className="col-span-4 bg-slate-100 text-slate-700 flex items-center justify-center rounded px-2 truncate border border-slate-200"
            title="APM Terminal Care (08:00 - 14:30 UTC)"
          >
            <Building2 className="w-3 h-3 mr-1 text-slate-500 shrink-0" />
            <span className="truncate text-[11px] font-medium">APM Terminal (08:00-14:30)</span>
          </div>

          {/* Apex Drayage Custody (With Breach Marker) */}
          <div 
            className="col-span-6 bg-blue-50 text-blue-900 border border-blue-300 flex items-center justify-between rounded px-2.5 truncate"
            title="Apex Drayage Motor Transit (14:30 - 22:00 UTC) - INCLUDES CRITICAL BREACH"
          >
            <div className="flex items-center truncate">
              <Truck className="w-3.5 h-3.5 mr-1.5 text-blue-700 shrink-0" />
              <span className="truncate font-bold text-blue-950 text-[11px]">Apex Drayage Active Custody</span>
            </div>

            <div className="flex items-center gap-1 bg-red-100 border border-red-300 text-red-800 px-1.5 py-0.5 rounded text-[10px] font-bold">
              <AlertTriangle className="w-2.5 h-2.5 text-red-600" />
              <span>17:15 Breach</span>
            </div>
          </div>

          {/* Consignee */}
          <div 
            className="col-span-2 bg-slate-100 text-slate-600 flex items-center justify-center rounded px-1 truncate border border-slate-200"
            title="Consignee Ingate Delivery"
          >
            <span className="truncate text-[11px]">Consignee</span>
          </div>
        </div>
      </div>

      {/* Chronological Event Stepper & Evidence Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left 2 Cols: Timeline Nodes */}
        <div className="lg:col-span-2 space-y-2.5">
          {timeline.map((event, idx) => {
            const isSelected = selectedEvent?.event_id === event.event_id;
            const isBreach = event.is_breach;
            const isHandover = event.is_relevant_handover;

            return (
              <div
                key={event.event_id || idx}
                onClick={() => setSelectedEvent(event)}
                className={`p-3.5 rounded-lg border transition-all cursor-pointer flex items-start justify-between gap-3 ${
                  isBreach 
                    ? 'bg-red-50/80 border-red-300 hover:border-red-400' 
                    : isHandover
                    ? 'bg-blue-50/80 border-blue-300 hover:border-blue-400'
                    : isSelected
                    ? 'bg-white border-blue-400 shadow-sm'
                    : 'bg-white border-slate-200 hover:bg-slate-50'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded-lg shrink-0 mt-0.5 ${
                    isBreach 
                      ? 'bg-red-100 text-red-700 border border-red-200' 
                      : isHandover
                      ? 'bg-blue-100 text-blue-700 border border-blue-200'
                      : 'bg-slate-100 text-slate-600 border border-slate-200'
                  }`}>
                    {isBreach ? (
                      <AlertTriangle className="w-4 h-4" />
                    ) : isHandover ? (
                      <FileCheck className="w-4 h-4" />
                    ) : (
                      <Clock className="w-4 h-4" />
                    )}
                  </div>

                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-bold text-slate-900">
                        {formatUtcTime(event.timestamp_utc)}
                      </span>
                      {isBreach && (
                        <span className="badge badge-red text-[10px] font-bold">
                          Earliest Recorded Breach
                        </span>
                      )}
                      {isHandover && (
                        <span className="badge badge-blue text-[10px] font-bold">
                          Origin Gate Handover
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-700">
                      {event.description}
                    </p>
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3 h-3 text-slate-400" />
                        {event.location_name}
                      </span>
                      <span className="text-slate-300">•</span>
                      <span className="text-slate-600">
                        Custody: <strong className="text-slate-900">{event.active_custody_holder}</strong>
                      </span>
                    </div>
                  </div>
                </div>

                <ChevronRight className={`w-4 h-4 shrink-0 transition-transform mt-1 ${
                  isSelected ? 'text-blue-600 rotate-90' : 'text-slate-400'
                }`} />
              </div>
            );
          })}
        </div>

        {/* Right Col: Selected Event Evidence Detail */}
        <div className="glass-panel p-5 rounded-lg flex flex-col justify-between space-y-4 bg-white border-slate-200 shadow-xs">
          <div>
            <div className="flex items-center gap-2 text-xs font-bold text-slate-900 uppercase tracking-wider mb-3 pb-2 border-b border-slate-200">
              <Info className="w-3.5 h-3.5 text-blue-600" />
              <span>Event Evidence Detail</span>
            </div>

            {selectedEvent ? (
              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-slate-500 block text-[11px] font-semibold">TIMESTAMP (UTC)</span>
                  <span className="text-slate-900 font-bold text-xs">
                    {formatUtcTime(selectedEvent.timestamp_utc)}
                  </span>
                </div>

                <div>
                  <span className="text-slate-500 block text-[11px] font-semibold">EVENT CLASSIFICATION</span>
                  <span className="text-slate-800 bg-slate-100 px-2 py-1 rounded border border-slate-200 inline-block mt-0.5 font-bold">
                    {selectedEvent.event_type}
                  </span>
                </div>

                <div>
                  <span className="text-slate-500 block text-[11px] font-semibold">LOCATION</span>
                  <span className="text-slate-800 font-medium">{selectedEvent.location_name}</span>
                </div>

                <div>
                  <span className="text-slate-500 block text-[11px] font-semibold">ACTIVE CUSTODY HOLDER</span>
                  <span className="text-slate-900 font-bold">{selectedEvent.active_custody_holder}</span>
                </div>

                <div>
                  <span className="text-slate-500 block text-[11px] font-semibold">EVIDENTIARY SOURCE</span>
                  <span className="text-slate-700 bg-slate-100 px-2 py-1 rounded border border-slate-200 block mt-0.5 text-[11px] font-medium">
                    {selectedEvent.evidence_source || 'Verified Carrier Telemetry Time-Series'}
                  </span>
                </div>

                <div className="pt-2 border-t border-slate-200">
                  <span className="text-slate-500 block text-[11px] mb-1 font-bold">FORENSIC SIGNIFICANCE</span>
                  <p className="text-slate-700 text-xs leading-relaxed bg-slate-50 p-2.5 rounded border border-slate-200">
                    {selectedEvent.is_breach ? (
                      <span className="text-red-800 font-medium">
                        Critical threshold violation recorded strictly after gate outgate while under carrier's physical care. Establishes temporal liability.
                      </span>
                    ) : selectedEvent.is_relevant_handover ? (
                      <span className="text-blue-800 font-medium">
                        Driver signed origin gate receipt with 'CLEAN' condition remarks without exceptions, legally establishing equipment integrity upon pickup.
                      </span>
                    ) : (
                      <span>Corroborating chronological waypoint confirming continuous custody without gaps.</span>
                    )}
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-slate-500 text-xs italic">Select an event from the timeline to inspect evidence details.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
