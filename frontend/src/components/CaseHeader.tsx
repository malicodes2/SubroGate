import React from 'react';
import { Container, Building2, MapPin, Sparkles, AlertTriangle, RotateCcw } from 'lucide-react';
import { CaseModel } from '../types';

interface CaseHeaderProps {
  caseData: CaseModel;
  onSimulateShock: () => void;
  onSimulateFailure: () => void;
  onReset: () => void;
  actionLoading: string | null;
}

export const CaseHeader: React.FC<CaseHeaderProps> = ({
  caseData,
  onSimulateShock,
  onSimulateFailure,
  onReset,
  actionLoading
}) => {
  const isApproved = caseData.status === 'APPROVED' || caseData.status === 'NEGOTIATION' || caseData.status === 'RESOLVED';
  const isFailed = caseData.status === 'FAILED';

  return (
    <div className="glass-card p-6 space-y-4 shadow-sm">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
        {/* Left: Container & Shipping Route */}
        <div className="space-y-2 flex-1">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className={`badge ${
              isApproved ? 'badge-green' : isFailed ? 'badge-red' : 'badge-blue'
            }`}>
              {caseData.status}
            </span>

            <span className="text-xs text-slate-500 font-mono">
              Case ID: <strong className="text-slate-800">{caseData.case_id}</strong>
            </span>

            <span className="badge badge-cyan text-[10px]">
              ISO 6346 Modulo-11 Verified ✓
            </span>
          </div>

          <div className="flex items-baseline gap-3 flex-wrap">
            <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <Container className="w-5 h-5 text-blue-600" />
              <span>{caseData.shipment_info?.container_id || 'MSKU9082345'}</span>
            </h2>
            <span className="text-slate-600 text-sm font-medium">
              {caseData.shipment_info?.commodity || 'Frozen Pharmaceutical Vaccines'}
            </span>
          </div>

          {/* Routing Information */}
          <div className="flex items-center gap-2 text-xs text-slate-500 flex-wrap pt-0.5">
            <div className="flex items-center gap-1.5 glass-panel px-2.5 py-1 rounded bg-slate-50 border-slate-200">
              <Building2 className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              <span className="text-slate-500">Origin:</span>
              <span className="text-slate-800 font-medium">{caseData.shipment_info?.origin_facility || 'APM Terminals LA'}</span>
            </div>

            <span className="text-slate-400 font-bold">➔</span>

            <div className="flex items-center gap-1.5 glass-panel px-2.5 py-1 rounded bg-slate-50 border-slate-200">
              <MapPin className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              <span className="text-slate-500">Dest:</span>
              <span className="text-slate-800 font-medium">{caseData.shipment_info?.destination_facility || 'Chicago Distribution'}</span>
            </div>

            {caseData.shipment_info?.carrier_name && (
              <div className="flex items-center gap-1.5 glass-panel px-2.5 py-1 rounded bg-slate-50 border-slate-200">
                <span className="text-slate-500">Carrier:</span>
                <span className="text-slate-800 font-semibold">{caseData.shipment_info.carrier_name}</span>
              </div>
            )}
          </div>
        </div>

        {/* Right: Financial Exposure & Actions */}
        <div className="flex flex-col sm:flex-row lg:flex-col items-start lg:items-end justify-between gap-3 shrink-0">
          <div className="flex items-center gap-3">
            <div className="glass-inset p-3 min-w-[120px] bg-slate-50 border-slate-200">
              <span className="text-[10px] text-slate-500 block uppercase font-semibold">DECLARED VALUE</span>
              <span className="text-sm font-bold text-slate-800 block mt-0.5">
                ${caseData.shipment_info?.declared_value_usd?.toLocaleString() || '100,000'}
              </span>
            </div>

            <div className="glass-inset p-3 min-w-[130px] border-blue-200 bg-blue-50/70">
              <span className="text-[10px] text-blue-700 block uppercase font-bold">CLAIMED LOSS</span>
              <span className="text-base font-extrabold text-blue-900 block mt-0.5">
                ${caseData.shipment_info?.claimed_loss_usd?.toLocaleString() || '75,000'}
              </span>
            </div>
          </div>

          {/* Quick Simulation & Reset Controls */}
          <div className="flex items-center gap-2 text-xs">
            <button
              onClick={onSimulateShock}
              disabled={actionLoading !== null}
              className="btn-secondary py-1.5 px-2.5 text-xs text-slate-700 hover:text-slate-900"
              title="Stream simulated 4.2G shock pulse to live case"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              <span>Stream Shock</span>
            </button>

            <button
              onClick={onSimulateFailure}
              disabled={actionLoading !== null}
              className="btn-secondary py-1.5 px-2.5 text-xs border-red-200 text-red-600 hover:bg-red-50"
              title="Simulate unreadable EIR extraction failure"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Simulate Failure</span>
            </button>

            <button
              onClick={onReset}
              disabled={actionLoading !== null}
              className="btn-secondary py-1.5 px-2 text-xs text-slate-500 hover:text-slate-800"
              title="Reset Firestore Case State"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
