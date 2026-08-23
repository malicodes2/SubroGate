import React from 'react';
import { Plus, Sparkles, FileText, Activity, ShieldCheck, ArrowRight } from 'lucide-react';

interface LandingHeroProps {
  onStartNew: () => void;
  isLoading?: boolean;
}

export const LandingHero: React.FC<LandingHeroProps> = ({
  onStartNew,
  isLoading = false
}) => {
  return (
    <div className="glass-card p-8 sm:p-10 relative overflow-hidden text-center sm:text-left shadow-sm">
      {/* Background Decorative Blur Highlights (Light Mode) */}
      <div className="absolute -top-24 -right-24 w-96 h-96 bg-cyan-400/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 max-w-3xl space-y-5">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-semibold">
          <Sparkles className="w-3.5 h-3.5 text-blue-600" />
          <span>Agentic Incident Reconstruction for Cargo Disputes</span>
        </div>

        <div className="space-y-2">
          <h1 className="text-2xl sm:text-4xl font-bold tracking-tight text-slate-900 leading-tight">
            Reconstruct incidents with <span className="text-blue-700">evidence</span>, not assumptions.
          </h1>
          <p className="text-sm sm:text-base text-slate-600 max-w-2xl leading-relaxed">
            Connect fragmented custody documents, shipment telemetry, and supporting evidence to reconstruct cargo incidents and produce evidence-backed responsibility assessments.
          </p>
        </div>

        {/* Action Button */}
        <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
          <button
            onClick={onStartNew}
            disabled={isLoading}
            className="btn-primary w-full sm:w-auto py-2.5 px-6 text-sm shadow-md font-bold"
          >
            <Plus className="w-4 h-4" />
            <span>Start New Investigation</span>
            <ArrowRight className="w-4 h-4 ml-1 opacity-80" />
          </button>
        </div>

        <p className="text-xs text-slate-500 pt-1">
          Our research did not identify a publicly demonstrated system that combines physical custody documents and IoT telemetry into a single incident-reconstruction workflow.
        </p>

        {/* 3 Value Pillars */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-4 border-t border-slate-200/80">
          <div className="glass-panel p-3 rounded-lg flex items-start gap-2.5 text-xs text-slate-700">
            <FileText className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
            <div>
              <strong className="text-slate-900 block font-semibold">Multimodal OCR</strong>
              <span className="text-slate-500 text-[11px]">ISO 6346 checksums &amp; gate stamps</span>
            </div>
          </div>

          <div className="glass-panel p-3 rounded-lg flex items-start gap-2.5 text-xs text-slate-700">
            <Activity className="w-4 h-4 text-cyan-600 shrink-0 mt-0.5" />
            <div>
              <strong className="text-slate-900 block font-semibold">Deterministic Fusion</strong>
              <span className="text-slate-500 text-[11px]">UTC normalization &amp; breach pinpoint</span>
            </div>
          </div>

          <div className="glass-panel p-3 rounded-lg flex items-start gap-2.5 text-xs text-slate-700">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <strong className="text-slate-900 block font-semibold">Controlled Autonomy</strong>
              <span className="text-slate-500 text-[11px]">Human-in-the-loop subrogation desk</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
