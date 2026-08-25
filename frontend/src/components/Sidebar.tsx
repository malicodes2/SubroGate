import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { 
  Search, 
  Clock, 
  CheckCircle2, 
  AlertTriangle,
  Loader2,
  Layers,
  FilePlus2,
  FolderOpen
} from 'lucide-react';
import { apiClient } from '../api/client';
import { CaseModel } from '../types';

interface SidebarProps {
  onNewInvestigation: () => void;
  onNavigate?: () => void;
  refreshTrigger?: number; // Pass a counter to force refresh history
}

export const Sidebar: React.FC<SidebarProps> = ({ 
  onNewInvestigation, 
  onNavigate,
  refreshTrigger = 0
}) => {
  const [cases, setCases] = useState<CaseModel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const fetchCases = async () => {
      try {
        setIsLoading(true);
        const data = await apiClient.listCases();
        // Sort newest first
        const sorted = data.sort((a, b) => 
          new Date(b.created_at_utc).getTime() - new Date(a.created_at_utc).getTime()
        );
        setCases(sorted);
      } catch (err) {
        console.error('Failed to load case history:', err);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchCases();
  }, [refreshTrigger]);

  const filteredCases = cases.filter(c => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      c.case_id.toLowerCase().includes(q) ||
      c.shipment_info?.container_id?.toLowerCase().includes(q) ||
      c.shipment_info?.commodity?.toLowerCase().includes(q) ||
      c.status.toLowerCase().includes(q)
    );
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'APPROVED':
      case 'RESOLVED':
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />;
      case 'FAILED':
        return <AlertTriangle className="w-3.5 h-3.5 text-red-600" />;
      case 'ANALYZING':
        return <Loader2 className="w-3.5 h-3.5 text-blue-600 animate-spin" />;
      default:
        return <Clock className="w-3.5 h-3.5 text-amber-600" />;
    }
  };

  const getStatusDisplay = (status: string) => {
    return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  return (
    <div className="w-72 md:w-64 bg-white text-slate-700 flex flex-col h-full border-r border-slate-200 shrink-0 select-none">
      {/* Search & Actions */}
      <div className="p-3.5 border-b border-slate-200 bg-slate-50/70 space-y-2.5">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search container / cargo..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-white border border-slate-200 rounded-lg py-1.5 pl-9 pr-3 text-xs text-slate-700 placeholder:text-slate-400 focus:outline-hidden focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all shadow-xs"
          />
        </div>

        {/* Quick Nav Links */}
        <div className="grid grid-cols-2 gap-1.5 text-xs font-semibold">
          <button
            onClick={() => {
              if (onNavigate) onNavigate();
              onNewInvestigation();
            }}
            className="btn-primary py-1.5 px-2 text-[11px] flex items-center justify-center gap-1 shadow-xs"
          >
            <FilePlus2 className="w-3.5 h-3.5" />
            <span>New Case</span>
          </button>

          <NavLink
            to="/catalog"
            onClick={() => {
              if (onNavigate) onNavigate();
            }}
            className={({ isActive }) =>
              `py-1.5 px-2 rounded-lg text-[11px] flex items-center justify-center gap-1 border transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-700 border-blue-200 font-bold'
                  : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
              }`
            }
          >
            <Layers className="w-3.5 h-3.5 text-blue-600" />
            <span>Fleet (4)</span>
          </NavLink>
        </div>
      </div>

      {/* Case List */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-1">
        <div className="flex items-center justify-between px-1 pb-2 pt-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider font-mono">
          <span className="flex items-center gap-1.5">
            <FolderOpen className="w-3 h-3 text-slate-400" />
            Active Case Workspace
          </span>
          <span>{filteredCases.length}</span>
        </div>
        
        {isLoading ? (
          <div className="flex items-center justify-center p-6 text-slate-400">
            <Loader2 className="w-5 h-5 animate-spin" />
          </div>
        ) : filteredCases.length === 0 ? (
          <div className="px-3 py-6 text-xs text-slate-500 text-center italic">
            {searchQuery ? 'No cases match search.' : 'No previous cases found.'}
          </div>
        ) : (
          filteredCases.map((c) => {
            return (
              <NavLink
                key={c.case_id}
                to={`/cases/${c.case_id}`}
                onClick={() => {
                  if (onNavigate) onNavigate();
                }}
                className={({ isActive: isNavLinkActive }) => `
                  block p-3 rounded-xl border transition-all text-left w-full group mb-1.5
                  ${isNavLinkActive 
                    ? 'bg-blue-50/80 border-blue-300 shadow-xs ring-1 ring-blue-400/20' 
                    : 'bg-white border-slate-200/80 text-slate-600 hover:bg-slate-50 hover:border-slate-300 shadow-xs'
                  }
                `}
              >
                {({ isActive: isNavLinkActive }) => (
                  <>
                    <div className="flex items-center justify-between mb-1">
                      <span className={`font-mono text-xs font-bold ${isNavLinkActive ? 'text-blue-700' : 'text-slate-800'}`}>
                        {c.case_id.split('-').slice(0, 2).join('-')}
                        <span className="opacity-40">-{c.case_id.split('-').slice(2).join('-')}</span>
                      </span>
                      {getStatusIcon(c.status)}
                    </div>
                    
                    <div className={`text-xs truncate font-medium mb-1.5 ${isNavLinkActive ? 'text-slate-900' : 'text-slate-600'}`}>
                      {c.shipment_info?.commodity || 'Unknown Cargo'}
                    </div>
                    
                    <div className="flex items-center justify-between text-[10px] font-mono">
                      <span className={`px-1.5 py-0.5 rounded font-bold ${
                        c.status === 'APPROVED' || c.status === 'RESOLVED' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' :
                        c.status === 'FAILED' ? 'bg-red-50 text-red-700 border border-red-200' :
                        c.status === 'ANALYZING' ? 'bg-blue-50 text-blue-700 border border-blue-200' :
                        'bg-slate-100 text-slate-600'
                      }`}>
                        {getStatusDisplay(c.status)}
                      </span>
                      
                      <span className="text-slate-400">
                        {new Date(c.updated_at_utc).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                      </span>
                    </div>
                  </>
                )}
              </NavLink>
            );
          })
        )}
      </div>
    </div>
  );
};
