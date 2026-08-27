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
  shipmentInfo?: Record<string, any>;
}

export const TelemetryChart: React.FC<TelemetryChartProps> = ({ telemetryRef, shipmentInfo }) => {
  const [activeMetric, setActiveMetric] = useState<'all' | 'temp' | 'shock'>('all');
  const [hoveredPoint, setHoveredPoint] = useState<TelemetryPoint | null>(null);

  const points: TelemetryPoint[] = telemetryRef?.points || [];

  // Determine dynamic temperature threshold limit
  const tempLimit = (() => {
    if (telemetryRef?.temp_limit_c !== undefined && telemetryRef?.temp_limit_c !== null) {
      return Number(telemetryRef.temp_limit_c);
    }
    const commLower = (shipmentInfo?.commodity || '').toLowerCase();
    if (commLower.includes('frozen') || commLower.includes('ice cream') || commLower.includes('seafood') || commLower.includes('meat') || commLower.includes('sub-zero')) {
      return -18.0;
    }
    // Check if points are deeply negative
    const avgTemp = points.length > 0 ? points.reduce((acc, p) => acc + p.temp, 0) / points.length : 0;
    if (avgTemp < -5) {
      return -18.0;
    }
    return 4.0;
  })();

  const shockLimit = telemetryRef?.shock_limit_g ?? 3.0;

  // Temperature excursion display
  const hasTempBreach = Boolean(
    telemetryRef?.has_temp_excursion || 
    (telemetryRef?.peak_temp_c !== undefined && telemetryRef?.peak_temp_c !== null && telemetryRef.peak_temp_c !== 0)
  );

  const tempExcursion = hasTempBreach 
    ? `${Number(telemetryRef?.peak_temp_c) > 0 ? '+' : ''}${Number(telemetryRef?.peak_temp_c).toFixed(1)}°C` 
    : 'Within Spec';

  const maxShock = telemetryRef?.peak_shock_g !== undefined && telemetryRef?.peak_shock_g !== null
    ? `${Number(telemetryRef.peak_shock_g).toFixed(1)}G`
    : (points.length > 0 ? `${Math.max(...points.map(p => p.shock)).toFixed(1)}G` : 'Normal');

  const custodian = telemetryRef?.breach_custodian || shipmentInfo?.carrier_name || 'In Transit Carrier';

  // SVG Geometry Constants
  const SVG_WIDTH = 600;
  const SVG_HEIGHT = 160;
  const PADDING_X = 40;
  const PADDING_Y = 20;
  const DRAW_WIDTH = SVG_WIDTH - PADDING_X * 2;
  const DRAW_HEIGHT = SVG_HEIGHT - PADDING_Y * 2;

  // Dynamic range boundaries for temperature
  const tempMinRange = tempLimit < 0 ? -30 : -20;
  const tempMaxRange = tempLimit < 0 ? 10 : 30;

  const normalizeY = (val: number, min: number, max: number) => {
    const ratio = Math.max(0, Math.min(1, (val - min) / (max - min)));
    return SVG_HEIGHT - PADDING_Y - ratio * DRAW_HEIGHT;
  };

  const getX = (index: number) => {
    if (points.length <= 1) return PADDING_X + DRAW_WIDTH / 2;
    return PADDING_X + (index / (points.length - 1)) * DRAW_WIDTH;
  };

  const tempPath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${normalizeY(p.temp, tempMinRange, tempMaxRange)}`).join(' ');
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
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="glass-inset p-3 border-slate-200 bg-slate-50/70">
            <span className="text-[10px] text-slate-700 uppercase font-bold">PEAK SHOCK FORCE</span>
            <div className="flex items-baseline gap-2 mt-0.5">
              <span className="text-lg font-extrabold text-slate-900 font-mono">{maxShock}</span>
              <span className="text-[10px] text-slate-600 font-semibold font-mono">
                (Limit: {shockLimit.toFixed(1)}G)
              </span>
            </div>
            <span className="text-[11px] text-slate-500 block mt-0.5">
              {Number(telemetryRef?.peak_shock_g) > shockLimit ? 'Exceeded Limit' : 'Recorded Impact'}
            </span>
          </div>

          <div className="glass-inset p-3 border-slate-200 bg-slate-50/70">
            <span className="text-[10px] text-slate-700 uppercase font-bold">TEMPERATURE EXCURSION</span>
            <div className="flex items-baseline gap-2 mt-0.5">
              <span className={`text-lg font-extrabold font-mono ${hasTempBreach ? 'text-red-700' : 'text-emerald-700'}`}>
                {tempExcursion}
              </span>
              <span className="text-[10px] text-slate-600 font-semibold font-mono">
                (Limit: {tempLimit > 0 ? `+${tempLimit.toFixed(1)}` : tempLimit.toFixed(1)}°C)
              </span>
            </div>
            <span className="text-[11px] text-slate-500 block mt-0.5">
              {hasTempBreach ? 'Thermal Setpoint Excursion' : 'No Excursion Recorded'}
            </span>
          </div>

          <div className="glass-inset p-3 bg-slate-50 border-slate-200">
            <span className="text-[10px] text-slate-500 uppercase font-semibold">CUSTODIAN AT BREACH</span>
            <span className="text-sm font-bold text-slate-900 block mt-0.5 truncate">{custodian}</span>
            <span className="text-[11px] text-slate-500 block mt-0.5">Post-interchange</span>
          </div>
        </div>

        <div className="p-4 rounded-lg bg-white border border-slate-200 shadow-xs space-y-2 flex-1 flex flex-col justify-center">
          <div className="flex items-center justify-between text-xs text-slate-500 pb-1 border-b border-slate-100">
            <span className="flex items-center gap-1.5 text-slate-700 font-semibold">
              <Clock className="w-3.5 h-3.5 text-blue-600" />
              Time-Series Profile (UTC Synchronized)
            </span>
            <span className="text-[10px] font-mono text-slate-400">
              Calibrated Threshold: {tempLimit > 0 ? `+${tempLimit.toFixed(1)}` : tempLimit.toFixed(1)}°C / {shockLimit.toFixed(1)}G
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
                <line x1={PADDING_X} y1={normalizeY(tempMaxRange, tempMinRange, tempMaxRange)} x2={SVG_WIDTH - PADDING_X} y2={normalizeY(tempMaxRange, tempMinRange, tempMaxRange)} stroke="#E2E8F0" strokeDasharray="3 3" strokeWidth="1" />
                <line x1={PADDING_X} y1={normalizeY(tempLimit, tempMinRange, tempMaxRange)} x2={SVG_WIDTH - PADDING_X} y2={normalizeY(tempLimit, tempMinRange, tempMaxRange)} stroke="#F59E0B" strokeDasharray="2 2" strokeWidth="1.2" />
                <line x1={PADDING_X} y1={normalizeY(tempMinRange, tempMinRange, tempMaxRange)} x2={SVG_WIDTH - PADDING_X} y2={normalizeY(tempMinRange, tempMinRange, tempMaxRange)} stroke="#E2E8F0" strokeDasharray="3 3" strokeWidth="1" />
                
                {/* Y-Axis Labels (Temp) */}
                <text x="35" y={normalizeY(tempMaxRange, tempMinRange, tempMaxRange) + 4} fill="#64748B" fontSize="9" textAnchor="end" fontFamily="sans-serif">
                  {tempMaxRange > 0 ? `+${tempMaxRange}` : tempMaxRange}°C
                </text>
                <text x="35" y={normalizeY(tempLimit, tempMinRange, tempMaxRange) + 4} fill="#D97706" fontSize="9" textAnchor="end" fontFamily="sans-serif">
                  {tempLimit > 0 ? `+${tempLimit}` : tempLimit}°C
                </text>
                <text x="35" y={normalizeY(tempMinRange, tempMinRange, tempMaxRange) + 4} fill="#64748B" fontSize="9" textAnchor="end" fontFamily="sans-serif">
                  {tempMinRange}°C
                </text>

                {/* Temperature Curve */}
                {(activeMetric === 'all' || activeMetric === 'temp') && (
                  <path d={tempPath} fill="none" stroke="#2563EB" strokeWidth="2.5" />
                )}

                {/* Shock Curve */}
                {(activeMetric === 'all' || activeMetric === 'shock') && (
                  <path d={shockPath} fill="none" stroke="#D97706" strokeWidth="2.5" />
                )}

                {/* Interactive Hover Nodes */}
                {points.map((p, idx) => {
                  const cx = getX(idx);
                  const cyTemp = normalizeY(p.temp, tempMinRange, tempMaxRange);
                  const cyShock = normalizeY(p.shock, 0, 5);
                  
                  return (
                    <g key={idx} onMouseEnter={() => setHoveredPoint(p)}>
                      {/* Invisible hover target */}
                      <rect x={cx - 10} y={0} width={20} height={SVG_HEIGHT} fill="transparent" className="cursor-pointer" />
                      {(activeMetric === 'all' || activeMetric === 'temp') && (
                        <circle cx={cx} cy={cyTemp} r={4} className="fill-blue-600 hover:fill-cyan-500 transition-colors pointer-events-none" />
                      )}
                      {(activeMetric === 'all' || activeMetric === 'shock') && (
                        <circle cx={cx} cy={cyShock} r={4} className="fill-amber-600 hover:fill-amber-500 transition-colors pointer-events-none" />
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

          {/* Hover Tooltip Footer */}
          {hoveredPoint && (
            <div className="text-[11px] font-mono text-slate-600 bg-slate-50 p-2 rounded border border-slate-200 flex items-center justify-between">
              <span>Time: <strong>{hoveredPoint.time} UTC</strong></span>
              <span>Temp: <strong>{hoveredPoint.temp > 0 ? `+${hoveredPoint.temp}` : hoveredPoint.temp}°C</strong></span>
              <span>Shock: <strong>{hoveredPoint.shock}G</strong></span>
              <span>Custody: <strong>{hoveredPoint.custody}</strong></span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
