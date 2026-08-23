import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { 
  Search, 
  Clock, 
  CheckCircle2, 
  AlertTriangle,
  Loader2,
  Container
} from 'lucide-react';
import { apiClient } from '../api/client';
import { CaseModel } from '../types';
import logoImg from '../assets/logo.png';

interface SidebarProps {
  onNewInvestigation: () => void;
  refreshTrigger?: number; // Pass a counter to force refresh history
}

export const Sidebar: React.FC<SidebarProps> = ({ 
  onNewInvestigation, 
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
    <div className="w-64 bg-slate-900 text-slate-300 flex flex-col h-screen border-r border-slate-800 shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 bg-slate-900/50">
        <div className="flex items-center gap-3">
          <img 
            src={logoImg} 
            alt="SubroGate Logo" 
            className="h-8 object-contain select-none"
          />
          <span className="font-heading font-bold text-lg text-white tracking-wide">SubroGate</span>
        </div>
      </div>

      {/* Search */}
      <div className="p-4 border-b border-slate-800 bg-slate-900/30">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-2.5 top-2.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search cases..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-md py-1.5 pl-8 pr-3 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
          />
        </div>
      </div>

      {/* Case List */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1">
        <div className="px-2 py-2 text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">
          Recent Cases
        </div>
        
        {isLoading ? (
          <div className="flex items-center justify-center p-4 text-slate-500">
            <Loader2 className="w-5 h-5 animate-spin" />
          </div>
        ) : filteredCases.length === 0 ? (
          <div className="px-3 py-4 text-xs text-slate-500 text-center italic">
            {searchQuery ? 'No cases match your search.' : 'No previous cases found.'}
          </div>
        ) : (
          filteredCases.map((c) => {
            return (
              <NavLink
                key={c.case_id}
                to={`/cases/${c.case_id}`}
                className={({ isActive: isNavLinkActive }) => `
                  block p-2.5 rounded-lg border transition-all text-left w-full group
                  ${isNavLinkActive 
                    ? 'bg-blue-900/40 border-blue-700/50 text-blue-100 shadow-sm' 
                    : 'bg-transparent border-transparent text-slate-400 hover:bg-slate-800 hover:text-slate-200 hover:border-slate-700'
                  }
                `}
              >
                {({ isActive: isNavLinkActive }) => (
                  <>
                    <div className="flex items-center justify-between mb-1">
                      <span className={`font-mono text-xs font-bold ${isNavLinkActive ? 'text-blue-300' : 'text-slate-300 group-hover:text-white'}`}>
                        {c.case_id.split('-').slice(0, 2).join('-')}
                        <span className="opacity-50">-{c.case_id.split('-').slice(2).join('-')}</span>
                      </span>
                      {getStatusIcon(c.status)}
                    </div>
                    
                    <div className="text-xs truncate font-medium mb-1">
                      {c.shipment_info?.commodity || 'Unknown Cargo'}
                    </div>
                    
                    <div className="flex items-center justify-between text-[10px]">
                      <span className={`px-1.5 py-0.5 rounded font-mono ${
                        c.status === 'APPROVED' ? 'bg-emerald-900/30 text-emerald-400' :
                        c.status === 'FAILED' ? 'bg-red-900/30 text-red-400' :
                        c.status === 'ANALYZING' ? 'bg-blue-900/30 text-blue-400' :
                        'bg-slate-800 text-slate-400'
                      }`}>
                        {getStatusDisplay(c.status)}
                      </span>
                      
                      <span className="text-slate-500">
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

      {/* Footer */}
      <div className="p-4 border-t border-slate-800 text-[10px] text-center text-slate-500 font-mono">
        SubroGate v2.0 <br/>
        Persistent Case Workspace
      </div>
    </div>
  );
};
