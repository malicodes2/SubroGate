import React from 'react';
import { FileText } from 'lucide-react';

interface DocumentViewerProps {
  containerId?: string;
  eirData?: Record<string, any>;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  containerId = 'N/A',
  eirData
}) => {
  const gateEvent = eirData?.gate_event_type || 'N/A';
  const handoverTime = eirData?.handover_timestamp_utc || 'N/A';
  const conditionRemarks = eirData?.damage_remarks || 'N/A';
  const sha256 = eirData?.sha256_fingerprint || 'N/A';
  const issuingFacility = eirData?.issuing_facility || 'N/A';
  const receivingCarrier = eirData?.receiving_party || 'N/A';

  return (
    <div className="glass-card flex flex-col h-full overflow-hidden shadow-sm">
      {/* Top Header */}
      <div className="px-5 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-blue-600" />
          <span className="font-bold text-slate-800">
            APM_Pier400_GateReceipt_{containerId}.pdf
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="badge badge-green text-[10px]">
            OCR Verified ✓
          </span>
          <span className="badge badge-cyan text-[10px]">
            SHA-256 Indexed
          </span>
        </div>
      </div>

      {/* Document Canvas Container with Fixed Proportions & Contain */}
      <div className="flex-1 overflow-y-auto bg-slate-100/70 p-4 sm:p-6 flex items-center justify-center">
        {/* Authentic Letter-Proportioned Physical EIR Scan (No stretch, max width 560px) */}
        <div className="w-full max-w-[560px] bg-white text-[#1E293B] shadow-md rounded p-6 sm:p-7 font-mono text-xs border border-slate-300 select-text">
          {/* Header */}
          <div className="border-b-2 border-[#334155] pb-3 mb-4 flex items-start justify-between">
            <div>
              <h3 className="text-base font-black tracking-tight text-[#0F172A] uppercase font-sans">
                APM TERMINALS PACIFIC
              </h3>
              <p className="text-[10px] text-[#475569] font-sans font-medium">
                Pier 400 Los Angeles, CA 90731 • Gate Interchange Receipt (EIR)
              </p>
              <p className="text-[9px] text-[#64748B]">TOS GATE TRANSACTION ID: TXN-2026-0815-98420</p>
            </div>

            {/* Rubber Stamp */}
            <div className="border-2 border-[#15803D] text-[#15803D] px-2.5 py-1 rounded text-center rotate-[-3deg] uppercase font-bold text-[10px] leading-tight">
              <span>OUTGATE LOADED</span>
              <span className="block text-[8px] font-mono">CLEAN INSPECTION</span>
            </div>
          </div>

          {/* Barcode & ISO Container ID Banner */}
          <div className="bg-[#F8FAFC] p-2.5 rounded border border-[#CBD5E1] mb-3 flex items-center justify-between">
            <div>
              <span className="text-[9px] text-[#64748B] block uppercase font-sans font-semibold">EQUIPMENT IDENTIFIER (ISO 6346)</span>
              <div className="flex items-center gap-1 text-sm font-black text-[#0F172A]">
                <span className="bg-[#E2E8F0] px-1.5 py-0.5 rounded">{containerId || 'N/A'}</span>
              </div>
            </div>

            <div className="text-right">
              <span className="text-[9px] text-[#64748B] block uppercase font-sans font-semibold">SEAL NUMBER VERIFIED</span>
              <span className="text-xs font-bold text-[#0F172A]">SEAL-N/A</span>
            </div>
          </div>

          {/* Core Metadata Grid */}
          <div className="grid grid-cols-2 gap-2 text-[11px] mb-3 border border-[#E2E8F0] p-2.5 rounded bg-white">
            <div>
              <span className="text-[9px] text-[#64748B] block uppercase font-sans font-semibold">GATE EVENT / MOVEMENT</span>
              <strong className="text-[#0F172A]">{gateEvent}</strong>
            </div>

            <div>
              <span className="text-[9px] text-[#64748B] block uppercase font-sans font-semibold">HANDOVER TIMESTAMP (UTC)</span>
              <strong className="text-[#0F172A]">{handoverTime.replace('T', ' ').replace('Z', ' UTC')}</strong>
            </div>

            <div>
              <span className="text-[9px] text-[#64748B] block uppercase font-sans font-semibold">RELEASING FACILITY</span>
              <span className="text-[#334155]">{issuingFacility}</span>
            </div>

            <div>
              <span className="text-[9px] text-[#64748B] block uppercase font-sans font-semibold">RECEIVING CARRIER</span>
              <strong className="text-[#0F172A]">{receivingCarrier}</strong>
            </div>

            <div>
              <span className="text-[9px] text-[#64748B] block uppercase font-sans font-semibold">TRACTOR / TRUCK LICENSE</span>
              <span className="text-[#334155]">{eirData?.truck_license || 'N/A'}</span>
            </div>

            <div>
              <span className="text-[9px] text-[#64748B] block uppercase font-sans font-semibold">REEFER SET POINT</span>
              <span className="text-[#334155]">{eirData?.reefer_set_point || 'N/A'}</span>
            </div>
          </div>

          {/* Equipment Remarks Box */}
          <div className="border border-[#CBD5E1] p-2.5 rounded bg-[#F8FAFC] mb-3">
            <span className="text-[9px] text-[#475569] block font-bold uppercase font-sans mb-1">
              INSPECTION REMARKS &amp; PRE-EXISTING DEFECTS:
            </span>
            <p className="bg-[#DCFCE7]/90 text-[#166534] border border-[#86EFAC] p-2 rounded text-[11px] font-bold">
              &ldquo;{conditionRemarks}&rdquo;
            </p>
            <p className="text-[9px] text-[#64748B] mt-1 font-sans">
              Driver conducted walkaround inspection prior to terminal outgate. Zero structural or refrigeration defects recorded.
            </p>
          </div>

          {/* Signatures & Checksums */}
          <div className="border-t-2 border-[#334155] pt-2.5 flex items-center justify-between text-[9px] text-[#475569]">
            <div>
              <span className="block font-sans">DRIVER SIGN-OFF: <strong className="text-[#0F172A] italic text-[11px]">{eirData?.driver_name || 'N/A'}</strong></span>
              <span className="text-[8px] text-[#94A3B8]">BADGE ID: {eirData?.driver_badge || 'N/A'}</span>
            </div>

            <div className="text-right">
              <span className="block font-mono font-bold text-[#0F172A]">CLERK: {eirData?.clerk_name || 'N/A'}</span>
              <span className="text-[8px] font-mono text-[#64748B]">SHA-256: {sha256.slice(0, 16)}...</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
