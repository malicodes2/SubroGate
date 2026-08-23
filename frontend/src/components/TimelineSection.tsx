import React from 'react';
import { Clock, ShieldAlert, FileCheck, AlertTriangle, ArrowRight } from 'lucide-react';

interface TimelineEvent {
  event_id: string;
  timestamp_utc: string;
  event_type: string;
  description: string;
  is_breach?: boolean;
  is_relevant_handover?: boolean;
  evidence_source?: string;
}

interface TimelineSectionProps {
  timeline: TimelineEvent[];
}

export const TimelineSection: React.FC<TimelineSectionProps> = ({
  timeline
}) => {
  const formatTime = (isoString?: string) => {
    if (!isoString) return '--:--:--';
    try {
      const dt = new Date(isoString);
      return dt.toISOString().split('T')[1].substring(0, 8);
    } catch {
      return isoString;
    }
  };

  return (
    <div className="glass-card p-8 shadow-sm">
      <div className="flex items-center gap-3 pb-6 border-b border-slate-200 mb-6">
        <Clock className="w-6 h-6 text-slate-700" />
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            Incident Timeline
          </h2>
          <p className="text-sm text-slate-500">
            Chronological reconstruction from correlated evidence sources
          </p>
        </div>
      </div>

      <div className="relative border-l-2 border-slate-200 ml-4 space-y-8 pb-4">
        {timeline.map((event, idx) => {
          const isBreach = event.is_breach;
          const isHandover = event.is_relevant_handover;
          
          let icon = <div className="w-3 h-3 rounded-full bg-slate-300" />;
          if (isBreach) icon = <AlertTriangle className="w-4 h-4 text-white" />;
          if (isHandover) icon = <FileCheck className="w-4 h-4 text-white" />;

          return (
            <div key={event.event_id || idx} className="relative pl-8">
              {/* Timeline Node */}
              <div className={`absolute -left-[17px] top-1 w-8 h-8 rounded-full flex items-center justify-center border-4 border-white shadow-sm ${
                isBreach ? 'bg-red-500' : isHandover ? 'bg-blue-500' : 'bg-slate-200'
              }`}>
                {icon}
              </div>

              {/* Event Content */}
              <div className="flex flex-col sm:flex-row sm:items-start gap-2 sm:gap-6">
                
                {/* Time */}
                <div className="shrink-0 w-24">
                  <span className="text-sm font-bold text-slate-900 block">{formatTime(event.timestamp_utc)}</span>
                </div>

                {/* Details */}
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <h3 className={`text-base font-bold ${isBreach ? 'text-red-700' : isHandover ? 'text-blue-700' : 'text-slate-800'}`}>
                      {event.event_type}
                    </h3>
                    {event.evidence_source && (
                      <span className="text-[10px] uppercase font-bold tracking-widest text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                        {event.evidence_source}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-600 font-medium">
                    {event.description}
                  </p>
                </div>

              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
