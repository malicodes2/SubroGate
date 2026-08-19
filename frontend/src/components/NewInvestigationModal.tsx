import React, { useState, useMemo } from 'react';
import { 
  X, 
  Upload, 
  FileText, 
  Activity, 
  FileCheck, 
  CheckCircle2, 
  ArrowRight, 
  ArrowLeft, 
  Container, 
  Loader2, 
  Plus, 
  Trash2, 
  AlertTriangle 
} from 'lucide-react';
import { apiClient } from '../api/client';
import { CaseModel } from '../types';

interface NewInvestigationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCaseCreated: (createdCase: CaseModel) => void;
  isLiveMode?: boolean;
}

export const NewInvestigationModal: React.FC<NewInvestigationModalProps> = ({
  isOpen,
  onClose,
  onCaseCreated,
  isLiveMode = false
}) => {
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Step 1: Case Info State (Clean Empty State)
  const [containerId, setContainerId] = useState('');
  const [commodity, setCommodity] = useState('');
  const [declaredValue, setDeclaredValue] = useState('');
  const [claimedLoss, setClaimedLoss] = useState('');
  const [originFacility, setOriginFacility] = useState('');
  const [destinationFacility, setDestinationFacility] = useState('');
  const [carrierName, setCarrierName] = useState('');
  const [consigneeName, setConsigneeName] = useState('');

  // Step 2: Evidence Files State (Clean Empty State)
  const [eirFile, setEirFile] = useState<File | null>(null);
  const [telemetryFile, setTelemetryFile] = useState<File | null>(null);
  const [telemetryMeta, setTelemetryMeta] = useState<{
    rowCount: number;
    fileName: string;
  } | null>(null);

  // Step 3: Optional Supporting Docs
  const [bolNumber, setBolNumber] = useState('');
  const [optionalDocs, setOptionalDocs] = useState<{ id: string; name: string; type: string; size: string }[]>([]);
  const [isAddingDoc, setIsAddingDoc] = useState(false);
  const [newDocName, setNewDocName] = useState('');
  const [newDocType, setNewDocType] = useState('Contract/SLA');

  // STEP 1 VALIDATION LOGIC
  const step1Validation = useMemo(() => {
    const idTrim = containerId.trim();
    const idValid = idTrim.length >= 4;
    const isIsoFormat = /^[A-Z]{3}[UJZ]\d{6,7}$/i.test(idTrim);
    const commodityValid = commodity.trim().length > 0;
    const decVal = Number(declaredValue);
    const declaredValid = !isNaN(decVal) && decVal > 0;
    const claimVal = Number(claimedLoss);
    const lossValid = !isNaN(claimVal) && claimVal > 0;
    const lossExceedsDeclared = declaredValid && lossValid && claimVal > decVal;
    const carrierValid = carrierName.trim().length > 0;

    const isValid = idValid && commodityValid && declaredValid && lossValid && !lossExceedsDeclared && carrierValid;

    return {
      idValid,
      isIsoFormat,
      commodityValid,
      declaredValid,
      lossValid,
      lossExceedsDeclared,
      carrierValid,
      isValid
    };
  }, [containerId, commodity, declaredValue, claimedLoss, carrierName]);

  // STEP 2 VALIDATION LOGIC
  const step2Validation = useMemo(() => {
    const hasEir = Boolean(eirFile);
    const hasTelemetry = Boolean(telemetryFile);
    const isValid = hasEir && hasTelemetry;
    return { hasEir, hasTelemetry, isValid };
  }, [eirFile, telemetryFile]);

  if (!isOpen) return null;

  // Handle EIR File Upload
  const handleEirUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setEirFile(file);
      if (errorMsg) setErrorMsg(null);
    }
  };

  const handleRemoveEir = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEirFile(null);
  };

  // Handle Telemetry File Upload
  const handleTelemetryUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setTelemetryFile(file);
      const reader = new FileReader();
      reader.onload = (event) => {
        const text = event.target?.result as string;
        const lines = text.split('\n').filter(l => l.trim().length > 0);
        setTelemetryMeta({
          rowCount: Math.max(lines.length - 1, 1),
          fileName: file.name
        });
        if (errorMsg) setErrorMsg(null);
      };
      reader.readAsText(file);
    }
  };

  const handleRemoveTelemetry = (e: React.MouseEvent) => {
    e.stopPropagation();
    setTelemetryFile(null);
    setTelemetryMeta(null);
  };

  // Add Custom Optional Doc
  const handleAddOptionalDoc = () => {
    if (!newDocName.trim()) return;
    const doc = {
      id: Date.now().toString(),
      name: newDocName.trim().endsWith('.pdf') ? newDocName.trim() : `${newDocName.trim()}.pdf`,
      type: newDocType,
      size: `${(Math.random() * 1.5 + 0.5).toFixed(1)} MB`
    };
    setOptionalDocs([...optionalDocs, doc]);
    setNewDocName('');
    setIsAddingDoc(false);
  };

  const handleRemoveOptionalDoc = (id: string) => {
    setOptionalDocs(optionalDocs.filter(d => d.id !== id));
  };

  // Submit Investigation
  const handleExecuteAnalysis = async () => {
    if (!step1Validation.isValid) {
      setErrorMsg('Please complete all required shipment metadata fields before submitting.');
      setCurrentStep(1);
      return;
    }
    if (!step2Validation.isValid) {
      setErrorMsg('Both an EIR Document and Telemetry CSV are required before analyzing.');
      setCurrentStep(2);
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMsg(null);

      const formData = new FormData();
      formData.append('shipment_id', containerId.trim());
      formData.append('commodity', commodity.trim());
      formData.append('declared_value_usd', declaredValue);
      formData.append('claimed_loss_usd', claimedLoss);
      formData.append('origin_facility', originFacility.trim());
      formData.append('destination_facility', destinationFacility.trim());
      formData.append('carrier_name', carrierName.trim());

      if (eirFile) {
        formData.append('eir_file', eirFile);
      }
      if (telemetryFile) {
        formData.append('telemetry_file', telemetryFile);
      }

      const createdCase = await apiClient.submitNewInvestigation(formData);
      onCaseCreated(createdCase);
      onClose();
    } catch (err: any) {
      setErrorMsg(`Investigation processing error: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-fade-in">
      <div className="glass-card w-full max-w-3xl overflow-hidden shadow-2xl border-slate-300 bg-white flex flex-col max-h-[90vh]">
        {/* Modal Top Header (Light Mode) */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 flex items-center justify-center shadow-xs">
              <Container className="w-4 h-4" />
            </div>
            <div>
              <h2 className="font-heading font-bold text-sm text-slate-900 flex items-center gap-2">
                Initiate New Cargo Transit Investigation
              </h2>
              <p className="text-[11px] text-slate-500 font-sans">
                Multimodal custody extraction, timeline fusion, and evidence-backed assessment
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors"
            title="Close Wizard"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Step Indicator Bar */}
        <div className="grid grid-cols-4 border-b border-slate-200 bg-slate-100 text-[11px] font-mono select-none">
          {[
            { num: 1, label: 'Case Info' },
            { num: 2, label: 'Evidence Upload' },
            { num: 3, label: 'Supporting Docs' },
            { num: 4, label: 'Review & Analyze' }
          ].map((s) => (
            <div
              key={s.num}
              className={`py-2.5 px-3 flex items-center justify-center gap-2 border-r border-slate-200 last:border-r-0 cursor-default transition-colors ${
                currentStep === s.num
                  ? 'bg-white text-blue-700 font-bold border-b-2 border-b-blue-600 shadow-xs'
                  : currentStep > s.num
                  ? 'text-emerald-700 bg-emerald-50/60'
                  : 'text-slate-400 bg-slate-50'
              }`}
            >
              <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold ${
                currentStep === s.num
                  ? 'bg-blue-600 text-white'
                  : currentStep > s.num
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-200 text-slate-500'
              }`}>
                {currentStep > s.num ? '✓' : s.num}
              </span>
              <span className="hidden sm:inline">{s.label}</span>
            </div>
          ))}
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {errorMsg && (
            <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs font-mono flex items-start gap-2.5 shadow-xs">
              <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <strong className="block font-bold">Action Required</strong>
                <span>{errorMsg}</span>
              </div>
            </div>
          )}

          {/* STEP 1: Case Info & Metadata */}
          {currentStep === 1 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-900 uppercase tracking-wider font-mono">
                  1. Shipment &amp; Cargo Metadata
                </span>
                <span className="text-[10px] text-slate-400 font-mono">* Required fields must be completed to proceed</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 text-xs">
                {/* Container ID */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-slate-700 font-mono text-[10px] font-bold">
                      CONTAINER / SHIPMENT ID *
                    </label>
                    {step1Validation.isIsoFormat && (
                      <span className="text-[10px] text-emerald-700 font-mono font-semibold">ISO 6346 Format ✓</span>
                    )}
                  </div>
                  <input
                    type="text"
                    value={containerId}
                    onChange={(e) => {
                      setContainerId(e.target.value);
                      if (errorMsg) setErrorMsg(null);
                    }}
                    placeholder="e.g. MSKU9082345"
                    className={`w-full ${!step1Validation.idValid && containerId ? 'border-red-400 bg-red-50' : ''}`}
                  />
                  {!step1Validation.idValid && containerId && (
                    <span className="text-[10px] text-red-600 font-mono block mt-1">
                      Container / Shipment ID is required (min 4 characters).
                    </span>
                  )}
                </div>

                {/* Commodity */}
                <div>
                  <label className="text-slate-700 font-mono block text-[10px] font-bold mb-1">
                    COMMODITY / CARGO DESCRIPTION *
                  </label>
                  <input
                    type="text"
                    value={commodity}
                    onChange={(e) => {
                      setCommodity(e.target.value);
                      if (errorMsg) setErrorMsg(null);
                    }}
                    placeholder="e.g. Frozen Pharmaceutical Vaccines"
                    className={`w-full ${!step1Validation.commodityValid && commodity ? 'border-red-400 bg-red-50' : ''}`}
                  />
                </div>

                {/* Declared Value */}
                <div>
                  <label className="text-slate-700 font-mono block text-[10px] font-bold mb-1">
                    DECLARED VALUE (USD) *
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={declaredValue}
                    onChange={(e) => {
                      setDeclaredValue(e.target.value);
                      if (errorMsg) setErrorMsg(null);
                    }}
                    placeholder="e.g. 100000"
                    className={`w-full ${!step1Validation.declaredValid && declaredValue ? 'border-red-400 bg-red-50' : ''}`}
                  />
                </div>

                {/* Claimed Dispute Loss */}
                <div>
                  <label className="text-slate-700 font-mono block text-[10px] font-bold mb-1">
                    CLAIMED DISPUTE LOSS (USD) *
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={claimedLoss}
                    onChange={(e) => {
                      setClaimedLoss(e.target.value);
                      if (errorMsg) setErrorMsg(null);
                    }}
                    placeholder="e.g. 75000"
                    className={`w-full ${!step1Validation.lossValid && claimedLoss ? 'border-red-400 bg-red-50' : ''}`}
                  />
                  {step1Validation.lossExceedsDeclared && (
                    <span className="text-[10px] text-red-600 font-mono block mt-1">
                      Claimed loss cannot exceed declared value (${Number(declaredValue).toLocaleString()}).
                    </span>
                  )}
                </div>

                {/* Origin Facility */}
                <div>
                  <label className="text-slate-500 font-mono block text-[10px] mb-1 font-semibold">
                    ORIGIN TERMINAL / FACILITY
                  </label>
                  <input
                    type="text"
                    value={originFacility}
                    onChange={(e) => setOriginFacility(e.target.value)}
                    placeholder="e.g. APM Terminals Pier 400 Los Angeles, CA"
                  />
                </div>

                {/* Destination Facility */}
                <div>
                  <label className="text-slate-500 font-mono block text-[10px] mb-1 font-semibold">
                    DESTINATION FACILITY
                  </label>
                  <input
                    type="text"
                    value={destinationFacility}
                    onChange={(e) => setDestinationFacility(e.target.value)}
                    placeholder="e.g. Midwest Health Distribution Chicago, IL"
                  />
                </div>

                {/* Primary Carrier */}
                <div>
                  <label className="text-slate-700 font-mono block text-[10px] font-bold mb-1">
                    PRIMARY MOTOR / INTERMODAL CARRIER *
                  </label>
                  <input
                    type="text"
                    value={carrierName}
                    onChange={(e) => {
                      setCarrierName(e.target.value);
                      if (errorMsg) setErrorMsg(null);
                    }}
                    placeholder="e.g. Apex Drayage Logistics LLC"
                    className={`w-full ${!step1Validation.carrierValid && carrierName ? 'border-red-400 bg-red-50' : ''}`}
                  />
                </div>

                {/* Consignee */}
                <div>
                  <label className="text-slate-500 font-mono block text-[10px] mb-1 font-semibold">
                    CONSIGNEE RECIPIENT
                  </label>
                  <input
                    type="text"
                    value={consigneeName}
                    onChange={(e) => setConsigneeName(e.target.value)}
                    placeholder="e.g. Midwest Cold Chain Medical Inc."
                  />
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: Evidence Upload */}
          {currentStep === 2 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-900 uppercase tracking-wider font-mono">
                  2. Evidentiary Source Ingestion
                </span>
                <span className="text-[10px] text-slate-500 font-mono">EIR Document + Telemetry CSV Required</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Dropzone 1: EIR / Custody Document */}
                <div className="glass-inset p-4 rounded-lg flex flex-col justify-between space-y-3 bg-slate-50 border-slate-200">
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-bold text-slate-900 flex items-center gap-1.5 font-heading">
                        <FileText className="w-3.5 h-3.5 text-blue-600" />
                        EIR / Custody Document
                      </span>
                      <span className={`badge ${eirFile ? 'badge-green' : 'badge-neutral'} text-[9px]`}>
                        {eirFile ? 'Uploaded' : 'Required'}
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-500 font-sans mb-3">
                      Gate interchange receipt, equipment inspection, or signed bill of lading (PDF/PNG/JPG).
                    </p>

                    {eirFile ? (
                      <div className="border border-emerald-300 bg-emerald-50 rounded-lg p-3 flex items-center justify-between text-xs font-mono shadow-xs">
                        <div className="flex items-center gap-2 truncate">
                          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                          <div className="truncate">
                            <span className="truncate text-slate-900 font-bold block text-[11px]">
                              {eirFile.name}
                            </span>
                            <span className="text-[9px] text-slate-600 font-sans block">
                              {(eirFile.size / 1024).toFixed(1)} KB • File Ready
                            </span>
                          </div>
                        </div>
                        <button
                          onClick={handleRemoveEir}
                          className="p-1 rounded text-slate-400 hover:text-red-600 hover:bg-slate-100 transition-colors ml-2 shrink-0"
                          title="Remove uploaded EIR file"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ) : (
                      <label className="border border-dashed border-slate-300 hover:border-blue-500 rounded-lg p-4 flex flex-col items-center justify-center cursor-pointer bg-white hover:bg-blue-50/30 transition-colors text-center shadow-xs">
                        <Upload className="w-5 h-5 text-slate-400 mb-1.5" />
                        <span className="text-xs text-slate-800 font-semibold">Click to select EIR Document</span>
                        <span className="text-[10px] text-slate-400 font-mono mt-0.5">Supports PDF, PNG, JPG (max 25MB)</span>
                        <input
                          type="file"
                          accept=".pdf,.png,.jpg,.jpeg"
                          onChange={handleEirUpload}
                          className="hidden"
                        />
                      </label>
                    )}
                  </div>
                </div>

                {/* Dropzone 2: Telemetry CSV */}
                <div className="glass-inset p-4 rounded-lg flex flex-col justify-between space-y-3 bg-slate-50 border-slate-200">
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-bold text-slate-900 flex items-center gap-1.5 font-heading">
                        <Activity className="w-3.5 h-3.5 text-cyan-600" />
                        IoT Sensor Telemetry
                      </span>
                      <span className={`badge ${telemetryFile ? 'badge-green' : 'badge-neutral'} text-[9px]`}>
                        {telemetryFile ? 'Uploaded' : 'Required'}
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-500 font-sans mb-3">
                      Calibrated time-series CSV containing temperature, shock impact, and UTC timestamps.
                    </p>

                    {telemetryFile ? (
                      <div className="border border-emerald-300 bg-emerald-50 rounded-lg p-3 flex items-center justify-between text-xs font-mono shadow-xs">
                        <div className="space-y-1 truncate">
                          <div className="flex items-center gap-1.5 text-emerald-800 font-bold text-[11px]">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                            <span>{telemetryFile.name}</span>
                          </div>
                          <div className="text-[9px] text-slate-600 truncate">
                            {(telemetryFile.size / 1024).toFixed(1)} KB • {telemetryMeta?.rowCount || 'Valid'} samples
                          </div>
                        </div>
                        <button
                          onClick={handleRemoveTelemetry}
                          className="p-1 rounded text-slate-400 hover:text-red-600 hover:bg-slate-100 transition-colors ml-2 shrink-0"
                          title="Remove uploaded Telemetry CSV"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ) : (
                      <label className="border border-dashed border-slate-300 hover:border-blue-500 rounded-lg p-4 flex flex-col items-center justify-center cursor-pointer bg-white hover:bg-blue-50/30 transition-colors text-center shadow-xs">
                        <Upload className="w-5 h-5 text-slate-400 mb-1.5" />
                        <span className="text-xs text-slate-800 font-semibold">Click to select Telemetry CSV</span>
                        <span className="text-[10px] text-slate-400 font-mono mt-0.5">Supports standard IoT sensor CSV</span>
                        <input
                          type="file"
                          accept=".csv,.txt"
                          onChange={handleTelemetryUpload}
                          className="hidden"
                        />
                      </label>
                    )}
                  </div>
                </div>
              </div>

              {!step2Validation.isValid && (
                <div className="p-2.5 rounded-lg text-xs font-mono text-amber-800 flex items-center gap-2 border border-amber-300 bg-amber-50">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                  <span>Both an EIR Document and Telemetry CSV are required to proceed to analysis.</span>
                </div>
              )}
            </div>
          )}

          {/* STEP 3: Optional Supporting Documents */}
          {currentStep === 3 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-900 uppercase tracking-wider font-mono">
                  3. Optional Contractual &amp; Reference Material
                </span>
                <span className="badge badge-neutral text-[10px]">Optional</span>
              </div>

              <div className="space-y-3">
                <div className="text-xs">
                  <label className="text-slate-600 font-mono block text-[10px] mb-1 font-semibold">
                    BILL OF LADING / BOOKING NUMBER
                  </label>
                  <input
                    type="text"
                    value={bolNumber}
                    onChange={(e) => setBolNumber(e.target.value)}
                    placeholder="e.g. BOL-MSK-984210"
                  />
                </div>

                <div className="glass-inset p-3.5 rounded-lg space-y-2.5 bg-slate-50 border-slate-200">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-heading font-bold text-slate-900">
                      Attached Reference Documents ({optionalDocs.length})
                    </span>
                    <button
                      type="button"
                      onClick={() => setIsAddingDoc(!isAddingDoc)}
                      className="text-[11px] text-blue-600 hover:text-blue-800 font-bold font-mono flex items-center gap-1"
                    >
                      <Plus className="w-3 h-3" />
                      <span>{isAddingDoc ? 'Cancel' : 'Attach Reference'}</span>
                    </button>
                  </div>

                  {isAddingDoc && (
                    <div className="bg-white p-2.5 rounded border border-blue-200 space-y-2 text-xs font-mono shadow-xs">
                      <div className="grid grid-cols-2 gap-2">
                        <input
                          type="text"
                          value={newDocName}
                          onChange={(e) => setNewDocName(e.target.value)}
                          placeholder="Document name (e.g. Delivery_Receipt)"
                        />
                        <select
                          value={newDocType}
                          onChange={(e) => setNewDocType(e.target.value)}
                          className="text-xs font-mono bg-white border border-slate-300 rounded px-2"
                        >
                          <option value="Contract/SLA">Contract / SLA</option>
                          <option value="UIIA Agreement">UIIA Agreement</option>
                          <option value="Inspection Report">Inspection Report</option>
                          <option value="Commercial Invoice">Commercial Invoice</option>
                        </select>
                      </div>
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={handleAddOptionalDoc}
                          className="btn-primary text-xs py-1 px-3"
                        >
                          Add Document
                        </button>
                      </div>
                    </div>
                  )}

                  <div className="space-y-1.5">
                    {optionalDocs.length === 0 ? (
                      <p className="text-[10px] text-slate-400 italic py-1 font-mono">
                        No optional reference documents attached.
                      </p>
                    ) : (
                      optionalDocs.map((doc) => (
                        <div key={doc.id} className="bg-white p-2 rounded border border-slate-200 flex items-center justify-between text-xs font-mono shadow-xs">
                          <div className="flex items-center gap-2 truncate">
                            <FileCheck className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                            <span className="truncate text-slate-900 text-[11px] font-semibold">{doc.name}</span>
                            <span className="text-[9px] text-slate-500">({doc.type})</span>
                          </div>
                          <div className="flex items-center gap-2 shrink-0 ml-2">
                            <span className="text-[10px] text-slate-500 font-medium">{doc.size}</span>
                            <button
                              onClick={() => handleRemoveOptionalDoc(doc.id)}
                              className="p-1 text-slate-400 hover:text-red-600 transition-colors"
                              title="Remove document"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* STEP 4: Review & Incident Pipeline Analysis */}
          {currentStep === 4 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-900 uppercase tracking-wider font-mono">
                  4. Pre-Analysis Verification Summary
                </span>
                <span className="badge badge-green text-[10px]">All Prerequisites Satisfied ✓</span>
              </div>

              {/* Summary Dossier */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="glass-inset p-3 rounded-lg space-y-1.5 bg-slate-50 border-slate-200">
                  <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block font-bold">
                    SHIPMENT &amp; ROUTING
                  </span>
                  <div className="text-slate-700 font-mono space-y-0.5 text-[11px]">
                    <div>Container: <strong className="text-slate-900 font-bold">{containerId || 'N/A'}</strong></div>
                    <div>Commodity: {commodity || 'N/A'}</div>
                    <div>Claim: <strong className="text-emerald-700 font-bold">${Number(claimedLoss || 0).toLocaleString()} USD</strong></div>
                    <div className="truncate">Origin: {originFacility || 'Not specified'}</div>
                    <div className="truncate">Carrier: {carrierName || 'N/A'}</div>
                  </div>
                </div>

                <div className="glass-inset p-3 rounded-lg space-y-1.5 bg-slate-50 border-slate-200">
                  <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block font-bold">
                    EVIDENTIARY ASSETS
                  </span>
                  <div className="text-slate-700 font-mono space-y-0.5 text-[11px]">
                    <div className="flex items-center gap-1.5">
                      <span className="text-emerald-700 font-bold">✓</span>
                      <span>EIR Document: {eirFile?.name || 'Uploaded'}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-emerald-700 font-bold">✓</span>
                      <span>IoT Telemetry: {telemetryFile?.name || `${telemetryMeta?.rowCount || 0} samples`}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-emerald-700 font-bold">✓</span>
                      <span>Contract Reference: {bolNumber || 'None'} ({optionalDocs.length} attached)</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* SubroGate Automated Pipeline Preview */}
              <div className="glass-inset p-3.5 rounded-lg space-y-2 bg-slate-50 border-slate-200">
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block font-bold">
                  ANALYSIS EXECUTION PIPELINE
                </span>
                <div className="grid grid-cols-5 gap-1.5 text-center font-mono text-[9px]">
                  <div className="bg-white p-2 rounded border border-slate-200 text-slate-700 shadow-xs">
                    <strong className="block text-slate-900 text-[10px]">1. OCR</strong>
                    <span>EIR Extraction</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-slate-200 text-slate-700 shadow-xs">
                    <strong className="block text-slate-900 text-[10px]">2. TIME</strong>
                    <span>UTC Normalize</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-slate-200 text-slate-700 shadow-xs">
                    <strong className="block text-slate-900 text-[10px]">3. SENSOR</strong>
                    <span>Breach Anomaly</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-slate-200 text-slate-700 shadow-xs">
                    <strong className="block text-slate-900 text-[10px]">4. FUSION</strong>
                    <span>Custody Match</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-slate-200 text-slate-700 shadow-xs">
                    <strong className="block text-emerald-700 text-[10px]">5. AGENT</strong>
                    <span>Assessment</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer Controls */}
        <div className="px-6 py-3.5 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
          <div>
            {currentStep > 1 && (
              <button
                onClick={() => {
                  setErrorMsg(null);
                  setCurrentStep(currentStep - 1);
                }}
                disabled={isSubmitting}
                className="btn-secondary text-xs"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back</span>
              </button>
            )}
          </div>

          <div className="flex items-center gap-2.5">
            {currentStep < 4 ? (
              <button
                onClick={() => {
                  if (currentStep === 1 && !step1Validation.isValid) {
                    setErrorMsg('Please enter all required shipment metadata (*).');
                    return;
                  }
                  if (currentStep === 2 && !step2Validation.isValid) {
                    setErrorMsg('Both an EIR Document and Telemetry CSV are required to continue.');
                    return;
                  }
                  setErrorMsg(null);
                  setCurrentStep(currentStep + 1);
                }}
                className="btn-primary text-xs"
              >
                <span>Continue</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              <button
                onClick={handleExecuteAnalysis}
                disabled={isSubmitting}
                className="btn-primary text-xs shadow-md font-bold"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Analyzing Incident...</span>
                  </>
                ) : (
                  <>
                    <Activity className="w-3.5 h-3.5" />
                    <span>Analyze Incident</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
