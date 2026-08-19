import React from 'react';
import { RefreshCw, Server, Plus } from 'lucide-react';
import { ModelConfigInfo } from '../types';

interface NavbarProps {
  modelInfo?: ModelConfigInfo;
  isConnected: boolean;
  onRefresh: () => void;
  onNewInvestigation?: () => void;
  isLoading: boolean;
  caseStatus?: string;
  isLiveMode?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  modelInfo,
  isConnected,
  onRefresh,
  onNewInvestigation,
  isLoading,
  caseStatus,
  isLiveMode = false
}) => {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur-md px-6 py-3 shadow-sm">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand & Logo */}
        <div className="flex items-center gap-3.5">
          <img 
            src="/logo.png" 
            alt="SubroGate Logo" 
            className="h-8 sm:h-9 object-contain select-none"
          />
          <div className="hidden sm:block border-l border-slate-200 pl-3">
            <span className="text-xs text-slate-500 font-sans block leading-tight">
              Agentic Forensic Assessment for Cargo Transit Disputes
            </span>
          </div>
        </div>

        {/* Right Action Controls */}
        <div className="flex items-center gap-3">
          {/* Environment Status Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-50 border border-slate-200 text-xs">
            <Server className="w-3 h-3 text-slate-500" />
            <span className="text-[10px] text-slate-500">Mode:</span>
            <span className={`text-[10px] font-bold ${isLiveMode ? 'text-emerald-600' : 'text-cyan-700'}`}>
              {isLiveMode ? 'Live Cloud AI' : 'Demo / Local Mode'}
            </span>
          </div>

          {/* Start New Investigation Button */}
          {onNewInvestigation && (
            <button
              onClick={onNewInvestigation}
              className="btn-primary py-1.5 px-3 text-xs shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Start New Investigation</span>
              <span className="sm:hidden">New Case</span>
            </button>
          )}

          {/* Refresh Action */}
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="p-1.5 rounded-md bg-white hover:bg-slate-100 border border-slate-200 text-slate-600 hover:text-slate-900 transition-colors shadow-xs"
            title="Refresh System Health & Case State"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-blue-600' : ''}`} />
          </button>
        </div>
      </div>
    </header>
  );
};
