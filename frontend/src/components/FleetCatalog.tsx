import React, { useState, useEffect } from 'react';
import { Bot, ShieldCheck, FileCheck, Scale, Cpu, Terminal, ArrowRight, CheckCircle2, Lock, Sparkles, Layers } from 'lucide-react';
import { apiClient } from '../api/client';

interface AgentManifest {
  agent_id: string;
  name: string;
  version: string;
  category: string;
  role: string;
  model_binding: string;
  framework: string;
  human_gated: boolean;
  requires_scopes: string[];
  input_schema: Record<string, any>;
  output_schema: Record<string, any>;
  description: string;
  capabilities: string[];
}

export const FleetCatalog: React.FC = () => {
  const [agents, setAgents] = useState<AgentManifest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState<AgentManifest | null>(null);

  useEffect(() => {
    fetch('/agents')
      .then(res => res.json())
      .then(data => {
        if (data?.agents) {
          setAgents(data.agents);
          setSelectedAgent(data.agents[0] || null);
        }
      })
      .catch(err => console.error('Failed to load agent catalog:', err))
      .finally(() => setIsLoading(false));
  }, []);

  const getAgentIcon = (id: string) => {
    switch (id) {
      case 'investigator-agent':
        return <Bot className="w-5 h-5 text-blue-600" />;
      case 'settlement-agent':
        return <Scale className="w-5 h-5 text-emerald-600" />;
      case 'document-intelligence-agent':
        return <FileCheck className="w-5 h-5 text-cyan-600" />;
      case 'security-screening-agent':
        return <ShieldCheck className="w-5 h-5 text-purple-600" />;
      default:
        return <Cpu className="w-5 h-5 text-slate-600" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="glass-card p-6 border-slate-200 bg-white shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 flex items-center justify-center shadow-xs">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-slate-900 font-heading">
                SubroGate Agent Registry &amp; Fleet Catalog
              </h2>
              <span className="badge badge-blue text-[10px] font-bold">
                FEF Pillar 1: Discovery &amp; Registry
              </span>
            </div>
            <p className="text-xs text-slate-500 font-sans mt-0.5">
              Versioned institutional agent declarations, schema contracts, and Zero-Trust permission scopes
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-slate-600 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
          <span>Endpoint:</span>
          <code className="text-blue-700 font-bold">GET /agents</code>
        </div>
      </div>

      {/* 2-Column Fleet Explorer */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Agent List Column */}
        <div className="space-y-3">
          <h3 className="text-xs font-mono font-bold text-slate-500 uppercase tracking-wider px-1">
            Registered Institutional Agents ({agents.length})
          </h3>
          <div className="space-y-2">
            {agents.map((agent) => {
              const isSelected = selectedAgent?.agent_id === agent.agent_id;
              return (
                <button
                  key={agent.agent_id}
                  onClick={() => setSelectedAgent(agent)}
                  className={`w-full text-left p-4 rounded-xl transition-all border ${
                    isSelected
                      ? 'bg-white border-blue-500 shadow-md ring-1 ring-blue-500'
                      : 'bg-white/80 hover:bg-white border-slate-200 hover:border-slate-300 shadow-xs'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 shrink-0 mt-0.5">
                      {getAgentIcon(agent.agent_id)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1">
                        <strong className="text-xs font-bold text-slate-900 truncate block font-heading">
                          {agent.name}
                        </strong>
                        <span className="text-[10px] font-mono text-slate-400">v{agent.version}</span>
                      </div>
                      <p className="text-[11px] text-slate-500 truncate mt-0.5 font-sans">
                        {agent.role}
                      </p>
                      <div className="flex items-center gap-2 mt-2">
                        <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-700">
                          {agent.framework}
                        </span>
                        {agent.human_gated ? (
                          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 font-semibold">
                            Human Gated
                          </span>
                        ) : (
                          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold">
                            Autonomous
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Selected Agent Manifest Detail Column */}
        {selectedAgent && (
          <div className="lg:col-span-2 glass-card p-6 border-slate-200 bg-white shadow-sm space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-3">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-blue-50 border border-blue-200">
                  {getAgentIcon(selectedAgent.agent_id)}
                </div>
                <div>
                  <h3 className="font-heading font-bold text-base text-slate-900">
                    {selectedAgent.name}
                  </h3>
                  <p className="text-xs text-slate-500 font-mono">
                    ID: <code className="text-blue-700 font-bold">{selectedAgent.agent_id}</code> • Version: {selectedAgent.version}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs font-mono">
                <span className="text-slate-400">Model:</span>
                <span className="font-bold text-slate-800 bg-slate-100 px-2 py-1 rounded border border-slate-200">
                  {selectedAgent.model_binding}
                </span>
              </div>
            </div>

            {/* Description */}
            <div className="space-y-1.5">
              <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider">
                Purpose &amp; Scope
              </span>
              <p className="text-xs text-slate-700 leading-relaxed font-sans">
                {selectedAgent.description}
              </p>
            </div>

            {/* Capabilities */}
            <div className="space-y-2">
              <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider">
                Agent Capabilities
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                {selectedAgent.capabilities?.map((cap, i) => (
                  <div key={i} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center gap-2 text-slate-800 font-medium">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                    <span>{cap}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Security & Scopes */}
            <div className="space-y-2">
              <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider">
                Required Authorization Scopes (Zero-Trust)
              </span>
              <div className="flex flex-wrap gap-2">
                {selectedAgent.requires_scopes?.map((scope, i) => (
                  <span key={i} className="text-xs font-mono px-2.5 py-1 rounded-md bg-blue-50 text-blue-800 border border-blue-200 font-bold">
                    {scope}
                  </span>
                ))}
              </div>
            </div>

            {/* JSON Manifest Contract */}
            <div className="space-y-2 pt-2 border-t border-slate-100">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider">
                  Declarative Manifest Schema (GET /agents contract)
                </span>
              </div>
              <pre className="p-3.5 rounded-lg bg-slate-900 text-cyan-400 font-mono text-[11px] overflow-x-auto max-h-56 leading-relaxed select-text">
                {JSON.stringify(selectedAgent, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
