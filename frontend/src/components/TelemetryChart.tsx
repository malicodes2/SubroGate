import React, { useState } from 'react';
import { Activity, Clock, AlertTriangle } from 'lucide-react';

interface TelemetryPoint {
  time: string;
  temp: number;
  humidity: number;
  shock: number;
  custody: string;
  isBreach?: boolean;
}

interface TelemetryChartProps {
  telemetryRef?: Record<string, any>;
}

export const TelemetryChart: React.FC<TelemetryChartProps> = ({ telemetryRef }) => {
  const [activeMetric, setActiveMetric] = useState<'all' | 'temp' | 'shock'>('all');
  const [hoveredPoint, setHoveredPoint] = useState<TelemetryPoint | null>(null);

  const points: TelemetryPoint[] = [
    { time: '08:00 UTC', temp: -21.5, humidity: 45.2, shock: 0.2, custody: 'APM Terminal Pier 400' },
    { time: '11:00 UTC', temp: -21.2, humidity: 46.0, shock: 0.3, custody: 'APM Terminal Pier 400' },
    { time: '14:30 UTC', temp: -20.8, humidity: 44.8, shock: 0.5, custody: 'Origin Gate Handover (Apex Drayage)' },
    { time: '15:30 UTC', temp: -20.4, humidity: 47.1, shock: 0.6, custody: 'Apex Drayage (In-Transit I-15)' },
    { time: '17:15 UTC', temp: 12.4, humidity: 85.2, shock: 4.2, custody: 'Apex Drayage (Barstow Corridor)', isBreach: true },
    { time: '19:00 UTC', temp: 11.8, humidity: 84.1, shock: 0.4, custody: 'Apex Drayage (In-Transit)' },
    { time: '02:00 UTC', temp: 11.2, humidity: 83.0, shock: 0.3, custody: 'Apex Drayage (In-Transit)' },
    { time: '11:00 UTC', temp: 10.5, humidity: 82.0, shock: 0.3, custody: 'Consignee Facility (Chicago)' }
  ];

  return (
    <div className="glass-card flex flex-col h-full overflow-hidden shadow-sm">
      {/* Top Bar */}
      <div className="px-5 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-600" />
          <span className="font-bold text-slate-800">
            Continuous Sensor Telemetry (120 Calibrated Readings)
          </span>
        </div>

        {/* Metric Filter Tabs */}
        <div className="flex items-center gap-1 bg-slate-200/80 p-1 rounded-md text-xs">
          <button
            onClick={() => setActiveMetric('all')}
            className={`px-2.5 py-0.5 rounded text-xs transition-colors ${
              activeMetric === 'all' ? 'bg-white text-blue-700 font-bold shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            All Signals
          </button>
          <button
            onClick={() => setActiveMetric('temp')}
            className={`px-2.5 py-0.5 rounded text-xs transition-colors ${
              activeMetric === 'temp' ? 'bg-white text-blue-700 font-bold shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Temperature
          </button>
          <button
            onClick={() => setActiveMetric('shock')}
            className={`px-2.5 py-0.5 rounded text-xs transition-colors ${
              activeMetric === 'shock' ? 'bg-white text-blue-700 font-bold shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Shock Impact
          </button>
        </div>
      </div>

      <div className="p-5 flex-1 flex flex-col justify-between space-y-4">
        {/* KPI Strip */}
        <div className="grid grid-cols-3 gap-3">
          <div className="glass-inset p-3 border-red-200 bg-red-50/70">
            <span className="text-[10px] text-red-700 uppercase font-bold">PEAK SHOCK FORCE</span>
            <div className="flex items-baseline gap-2 mt-0.5">
              <span className="text-lg font-extrabold text-red-950 font-mono">4.2G</span>
              <span className="text-[10px] text-red-600 font-semibold">(Limit: 3.0G)</span>
            </div>
            <span className="text-[11px] text-red-800/80 block mt-0.5">17:15 UTC • Severe Transit Impact</span>
          </div>

          <div className="glass-inset p-3 border-amber-200 bg-amber-50/70">
            <span className="text-[10px] text-amber-700 uppercase font-bold">TEMPERATURE EXCURSION</span>
            <div className="flex items-baseline gap-2 mt-0.5">
              <span className="text-lg font-extrabold text-amber-950 font-mono">+12.4°C</span>
              <span className="text-[10px] text-amber-600 font-semibold">(Limit: +4.0°C)</span>
            </div>
            <span className="text-[11px] text-amber-800/80 block mt-0.5">Vaccine Protocol Breached</span>
          </div>

          <div className="glass-inset p-3 bg-slate-50 border-slate-200">
            <span className="text-[10px] text-slate-500 uppercase font-semibold">CUSTODIAN AT BREACH</span>
            <span className="text-sm font-bold text-slate-900 block mt-0.5">Apex Drayage Logistics</span>
            <span className="text-[11px] text-slate-500 block mt-0.5">+2.75h post-interchange</span>
          </div>
        </div>

        {/* Proportion-Accurate Non-Stretched SVG Chart on Light Canvas */}
        <div className="p-4 rounded-lg bg-white border border-slate-200 shadow-xs space-y-2 flex-1 flex flex-col justify-center">
          <div className="flex items-center justify-between text-xs text-slate-500 pb-1 border-b border-slate-100">
            <span className="flex items-center gap-1.5 text-slate-700 font-semibold">
              <Clock className="w-3.5 h-3.5 text-blue-600" />
              Time-Series Profile (UTC Synchronized)
            </span>
            <span className="text-red-600 font-bold flex items-center gap-1 text-[11px]">
              <AlertTriangle className="w-3.5 h-3.5" />
              A 4.2G shock occurred here (17:15 UTC)
            </span>
          </div>

          {/* SVG Canvas with fixed viewBox and proper aspect ratio */}
          <div className="w-full h-48 sm:h-52 relative bg-white">
            <svg 
              className="w-full h-full" 
              viewBox="0 0 600 160" 
              preserveAspectRatio="xMidYMid meet"
            >
              {/* Horizontal Reference Lines */}
              <line x1="40" y1="30" x2="580" y2="30" stroke="#E2E8F0" strokeDasharray="3 3" strokeWidth="1" />
              <line x1="40" y1="75" x2="580" y2="75" stroke="#E2E8F0" strokeDasharray="3 3" strokeWidth="1" />
              <line x1="40" y1="130" x2="580" y2="130" stroke="#E2E8F0" strokeDasharray="3 3" strokeWidth="1" />

              {/* Y-Axis Labels */}
              <text x="35" y="34" fill="#64748B" fontSize="9" textAnchor="end" fontFamily="sans-serif">+15°C</text>
              <text x="35" y="78" fill="#D97706" fontSize="9" textAnchor="end" fontFamily="sans-serif">+4°C</text>
              <text x="35" y="134" fill="#64748B" fontSize="9" textAnchor="end" fontFamily="sans-serif">-20°C</text>

              {/* Vaccine Upper Limit Line (+4.0°C at y=75) */}
              <line x1="40" y1="75" x2="580" y2="75" stroke="#F59E0B" strokeDasharray="2 2" strokeWidth="1.2" />
              <text x="45" y="70" fill="#B45309" fontSize="8" fontWeight="600" fontFamily="sans-serif">
                Vaccine Thermal Threshold (+4.0°C)
              </text>

              {/* Origin Gate Handover Marker (14:30 UTC -> x = 180) */}
              <line x1="180" y1="15" x2="180" y2="145" stroke="#2563EB" strokeWidth="1.5" strokeDasharray="4 2" />
              <text x="70" y="22" fill="#1D4ED8" fontSize="9" fontWeight="700" fontFamily="sans-serif">
                14:30 Handover (Apex Custody)
              </text>

              {/* Excursion Shaded Breach Zone (x = 270 to 570) */}
              <rect x="270" y="15" width="300" height="130" fill="rgba(239, 68, 68, 0.06)" rx="4" />
              <text x="320" y="142" fill="#B91C1C" fontSize="9" fontWeight="600" fontFamily="sans-serif">
                BREACH INTERVAL (Exclusive Apex Drayage Custody)
              </text>

              {/* Temperature Curve (Nominal -20°C -> Sudden Spike to +12.4°C at 17:15) */}
              {(activeMetric === 'all' || activeMetric === 'temp') && (
                <path
                  d="M 40 130 L 110 130 L 180 130 L 250 128 L 270 38 L 350 42 L 460 45 L 570 48"
                  fill="none"
                  stroke="#DC2626"
                  strokeWidth="2.5"
                />
              )}

              {/* Shock Spike at 17:15 (x = 270) */}
              {(activeMetric === 'all' || activeMetric === 'shock') && (
                <>
                  <line x1="270" y1="130" x2="270" y2="28" stroke="#D97706" strokeWidth="2.5" />
                  <circle cx="270" cy="28" r="4.5" fill="#D97706" />
                  <text x="278" y="28" fill="#B45309" fontSize="9" fontWeight="bold" fontFamily="sans-serif">
                    4.2G Shock Event
                  </text>
                </>
              )}

              {/* Interactive Hover Nodes */}
              {points.map((p, idx) => {
                const xPos = idx * 75 + 45;
                const yPos = p.isBreach ? 38 : 130;
                return (
                  <circle
                    key={idx}
                    cx={xPos}
                    cy={yPos}
                    r={4.5}
                    className="cursor-pointer fill-blue-600 hover:fill-cyan-500 transition-colors"
                    onMouseEnter={() => setHoveredPoint(p)}
                  />
                );
              })}
            </svg>
          </div>

          {/* Time Axis Markers */}
          <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-100">
            <span>08:00 APM Terminal</span>
            <span className="text-blue-700 font-semibold">14:30 Gate Outgate</span>
            <span className="text-red-700 font-bold">17:15 Shock &amp; Thermal Breach</span>
            <span>11:00 Delivery Rejected</span>
          </div>
        </div>

        {/* Hover Detail Strip */}
        {hoveredPoint && (
          <div className="glass-inset p-2.5 rounded text-xs flex items-center justify-between border-blue-200 bg-blue-50/50 animate-fade-in">
            <span className="text-slate-700 font-medium">
              Time: <strong className="text-slate-900">{hoveredPoint.time}</strong>
            </span>
            <div className="flex items-center gap-3">
              <span className="text-slate-700">Temp: <strong className={hoveredPoint.temp > 4 ? 'text-red-600' : 'text-emerald-600'}>{hoveredPoint.temp}°C</strong></span>
              <span className="text-slate-700">Shock: <strong className={hoveredPoint.shock > 3 ? 'text-red-600' : 'text-slate-900'}>{hoveredPoint.shock}G</strong></span>
              <span className="text-slate-700">Holder: <strong className="text-blue-800">{hoveredPoint.custody}</strong></span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
