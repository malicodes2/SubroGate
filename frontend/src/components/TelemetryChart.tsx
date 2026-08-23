import React, { useState } from 'react';
import { Activity, Clock } from 'lucide-react';

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

  const points: TelemetryPoint[] = telemetryRef?.points || [];
  const maxShock = telemetryRef?.peak_shock_g || 'N/A';
  const tempExcursion = telemetryRef?.peak_temp_c ? `+${telemetryRef.peak_temp_c}°C` : 'N/A';
  const custodian = telemetryRef?.breach_custodian || 'N/A';

  // SVG Geometry Constants
  const SVG_WIDTH = 600;
  const SVG_HEIGHT = 160;
  const PADDING_X = 40;
  const PADDING_Y = 20;
  const DRAW_WIDTH = SVG_WIDTH - PADDING_X * 2;
  const DRAW_HEIGHT = SVG_HEIGHT - PADDING_Y * 2;

  // Normalization logic to prevent distortion
  // Shock limits: 0G to 5G
  // Temp limits: -30C to +30C
  const normalizeY = (val: number, min: number, max: number) => {
    const ratio = Math.max(0, Math.min(1, (val - min) / (max - min)));
    return SVG_HEIGHT - PADDING_Y - ratio * DRAW_HEIGHT;
  };

  const getX = (index: number) => {
    if (points.length <= 1) return PADDING_X + DRAW_WIDTH / 2;
    return PADDING_X + (index / (points.length - 1)) * DRAW_WIDTH;
  };

  const tempPath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${normalizeY(p.temp, -30, 30)}`).join(' ');
  const shockPath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${normalizeY(p.shock, 0, 5)}`).join(' ');

  return (
    <div className="glass-card flex flex-col h-full overflow-hidden shadow-sm">
      {/* Top Bar */}
      <div className="px-5 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-600" />
          <span className="font-bold text-slate-800">
            Continuous Sensor Telemetry (Dynamic Readings)
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
          <div className="glass-inset p-3 border-slate-200 bg-slate-50/70">
            <span className="text-[10px] text-slate-700 uppercase font-bold">PEAK SHOCK FORCE</span>
            <div className="flex items-baseline gap-2 mt-0.5">
              <span className="text-lg font-extrabold text-slate-900 font-mono">{maxShock}G</span>
              <span className="text-[10px] text-slate-600 font-semibold">(Limit: 3.0G)</span>
            </div>
            <span className="text-[11px] text-slate-500 block mt-0.5">Recorded Impact</span>
          </div>

          <div className="glass-inset p-3 border-slate-200 bg-slate-50/70">
            <span className="text-[10px] text-slate-700 uppercase font-bold">TEMPERATURE EXCURSION</span>
            <div className="flex items-baseline gap-2 mt-0.5">
              <span className="text-lg font-extrabold text-slate-900 font-mono">{tempExcursion}</span>
              <span className="text-[10px] text-slate-600 font-semibold">(Limit: +4.0°C)</span>
            </div>
            <span className="text-[11px] text-slate-500 block mt-0.5">Thermal Threshold</span>
          </div>

          <div className="glass-inset p-3 bg-slate-50 border-slate-200">
            <span className="text-[10px] text-slate-500 uppercase font-semibold">CUSTODIAN AT BREACH</span>
            <span className="text-sm font-bold text-slate-900 block mt-0.5">{custodian}</span>
            <span className="text-[11px] text-slate-500 block mt-0.5">Post-interchange</span>
          </div>
        </div>

        <div className="p-4 rounded-lg bg-white border border-slate-200 shadow-xs space-y-2 flex-1 flex flex-col justify-center">
          <div className="flex items-center justify-between text-xs text-slate-500 pb-1 border-b border-slate-100">
            <span className="flex items-center gap-1.5 text-slate-700 font-semibold">
              <Clock className="w-3.5 h-3.5 text-blue-600" />
              Time-Series Profile (UTC Synchronized)
            </span>
          </div>

          {/* SVG Canvas with fixed viewBox and proper aspect ratio */}
          <div className="w-full h-48 sm:h-52 relative bg-white">
            {points.length > 0 ? (
              <svg 
                className="w-full h-full" 
                viewBox="0 0 600 160" 
                preserveAspectRatio="xMidYMid meet"
              >
                {/* Horizontal Reference Lines */}
                <line x1={PADDING_X} y1={normalizeY(30, -30, 30)} x2={SVG_WIDTH - PADDING_X} y2={normalizeY(30, -30, 30)} stroke="#E2E8F0" strokeDasharray="3 3" strokeWidth="1" />
                <line x1={PADDING_X} y1={normalizeY(4, -30, 30)} x2={SVG_WIDTH - PADDING_X} y2={normalizeY(4, -30, 30)} stroke="#F59E0B" strokeDasharray="2 2" strokeWidth="1.2" />
                <line x1={PADDING_X} y1={normalizeY(-20, -30, 30)} x2={SVG_WIDTH - PADDING_X} y2={normalizeY(-20, -30, 30)} stroke="#E2E8F0" strokeDasharray="3 3" strokeWidth="1" />
                
                {/* Y-Axis Labels (Temp) */}
                <text x="35" y={normalizeY(30, -30, 30) + 4} fill="#64748B" fontSize="9" textAnchor="end" fontFamily="sans-serif">+30°C</text>
                <text x="35" y={normalizeY(4, -30, 30) + 4} fill="#D97706" fontSize="9" textAnchor="end" fontFamily="sans-serif">+4°C</text>
                <text x="35" y={normalizeY(-20, -30, 30) + 4} fill="#64748B" fontSize="9" textAnchor="end" fontFamily="sans-serif">-20°C</text>

                {/* Temperature Curve */}
                {(activeMetric === 'all' || activeMetric === 'temp') && (
                  <path d={tempPath} fill="none" stroke="#DC2626" strokeWidth="2.5" />
                )}

                {/* Shock Curve */}
                {(activeMetric === 'all' || activeMetric === 'shock') && (
                  <path d={shockPath} fill="none" stroke="#D97706" strokeWidth="2.5" />
                )}

                {/* Interactive Hover Nodes */}
                {points.map((p, idx) => {
                  const cx = getX(idx);
                  const cyTemp = normalizeY(p.temp, -30, 30);
                  const cyShock = normalizeY(p.shock, 0, 5);
                  
                  return (
                    <g key={idx} onMouseEnter={() => setHoveredPoint(p)}>
                      {/* Invisible hover target */}
                      <rect x={cx - 10} y={0} width={20} height={SVG_HEIGHT} fill="transparent" className="cursor-pointer" />
                      {(activeMetric === 'all' || activeMetric === 'temp') && (
                        <circle cx={cx} cy={cyTemp} r={4.5} className="fill-blue-600 hover:fill-cyan-500 transition-colors pointer-events-none" />
                      )}
                      {(activeMetric === 'all' || activeMetric === 'shock') && (
                        <circle cx={cx} cy={cyShock} r={4.5} className="fill-amber-600 hover:fill-amber-500 transition-colors pointer-events-none" />
                      )}
                    </g>
                  );
                })}
              </svg>
            ) : (
              <div className="w-full h-full flex items-center justify-center text-sm font-semibold text-slate-400">
                Awaiting Telemetry Sync
              </div>
            )}
          </div>

          {/* Time Axis Markers */}
          <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-100">
            <span>Origin</span>
            <span className="text-blue-700 font-semibold">Gate Outgate</span>
            <span className="text-slate-500 font-bold">Transit</span>
            <span>Delivery</span>
          </div>
        </div>

        {/* Hover Detail Strip */}
        {hoveredPoint && (
          <div className="glass-inset p-2.5 rounded text-xs flex flex-wrap items-center justify-between border-blue-200 bg-blue-50/50 animate-fade-in gap-2">
            <span className="text-slate-700 font-medium whitespace-nowrap">
              Time: <strong className="text-slate-900">{hoveredPoint.time}</strong>
            </span>
            <div className="flex items-center flex-wrap gap-3">
              <span className="text-slate-700">Temp: <strong className={hoveredPoint.temp > 4 ? 'text-red-600' : 'text-emerald-600'}>{hoveredPoint.temp}°C</strong></span>
              <span className="text-slate-700">Shock: <strong className={hoveredPoint.shock > 3 ? 'text-red-600' : 'text-slate-900'}>{hoveredPoint.shock}G</strong></span>
              <span className="text-slate-700 truncate max-w-[150px] sm:max-w-xs" title={hoveredPoint.custody}>Holder: <strong className="text-blue-800">{hoveredPoint.custody}</strong></span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
