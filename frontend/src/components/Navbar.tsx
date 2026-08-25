import React from 'react';
import { NavLink } from 'react-router-dom';
import { RefreshCw, Server, Plus, Menu, Layers } from 'lucide-react';
import { ModelConfigInfo } from '../types';
import logoImg from '../assets/logo.png';

interface NavbarProps {
  modelInfo?: ModelConfigInfo;
  isConnected: boolean;
  onRefresh: () => void;
  onNewInvestigation?: () => void;
  onMenuClick?: () => void;
  isLoading: boolean;
  caseStatus?: string;
  isLiveMode?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  modelInfo,
  isConnected,
  onRefresh,
  onNewInvestigation,
  onMenuClick,
  isLoading,
  caseStatus,
  isLiveMode = false
}) => {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/90 backdrop-blur-md px-4 sm:px-6 py-2.5 shadow-xs">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand & Hamburger */}
        <div className="flex items-center gap-2 sm:gap-3.5">
          {/* Mobile Hamburger Button */}
          {onMenuClick && (
            <button
              onClick={onMenuClick}
              className="md:hidden p-2 -ml-1.5 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors focus:outline-hidden focus:ring-2 focus:ring-blue-500"
              aria-label="Open sidebar navigation"
            >
              <Menu className="w-5 h-5" />
            </button>
          )}

          <NavLink to="/" className="flex items-center gap-3 select-none">
            <img 
              src={logoImg} 
              alt="SubroGate Logo" 
              className="h-7 sm:h-8 object-contain select-none"
            />
          </NavLink>

          <div className="hidden lg:block border-l border-slate-200 pl-3">
            <span className="text-xs text-slate-500 font-sans block leading-tight">
              Agentic Forensic Assessment for Cargo Transit Disputes
            </span>
          </div>
        </div>

        {/* Center/Right Nav Links & Action Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Fleet Catalog Nav Link */}
          <NavLink
            to="/catalog"
            className={({ isActive }) =>
              `hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-700 border border-blue-200'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`
            }
          >
            <Layers className="w-3.5 h-3.5 text-blue-600" />
            <span>Agent Catalog</span>
          </NavLink>

          {/* AI Model Status Badge */}
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-50 border border-slate-200 text-xs">
            <Server className="w-3 h-3 text-cyan-600" />
            <span className="text-[10px] text-slate-500">Model:</span>
            <span className="text-[10px] font-bold text-cyan-700 font-mono">
              {modelInfo?.configured_model || 'Gemini 3.5 (Vertex AI)'}
            </span>
          </div>

          {/* Start New Investigation Button */}
          {onNewInvestigation && (
            <button
              onClick={onNewInvestigation}
              className="btn-primary py-1.5 px-3 text-xs shadow-xs"
            >
              <Plus className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Start New Investigation</span>
              <span className="sm:hidden">New Case</span>
            </button>
          )}

          {/* Refresh Status Button */}
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
            title="Refresh system connection"
            aria-label="Refresh system status"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-blue-600' : ''}`} />
          </button>
        </div>
      </div>
    </header>
  );
};
