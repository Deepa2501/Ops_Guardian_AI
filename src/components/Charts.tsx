import React from 'react';
import { TelemetryPoint } from '../types';

interface SparklineProps {
  data: TelemetryPoint[];
  field: keyof TelemetryPoint;
  color?: string;
  alertThreshold?: number;
  height?: number;
  width?: number;
  label?: string;
  unit?: string;
}

/**
 * Lightweight SVG sparkline — no external chart dependencies.
 * Renders a smooth time-series line with optional alert threshold marker.
 */
export function Sparkline({
  data,
  field,
  color = '#f97316',
  alertThreshold,
  height = 48,
  width = 160,
  label,
  unit,
}: SparklineProps) {
  if (!data || data.length < 2) {
    return (
      <svg width={width} height={height} className="opacity-30">
        <text x="50%" y="50%" textAnchor="middle" fill="#6b7280" fontSize="10">
          No data
        </text>
      </svg>
    );
  }

  const values = data.map((d) => Number(d[field]) || 0);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const pad = 4;
  const w = width - pad * 2;
  const h = height - pad * 2;

  const toX = (i: number) => pad + (i / (values.length - 1)) * w;
  const toY = (v: number) => pad + h - ((v - min) / range) * h;

  const points = values.map((v, i) => `${toX(i).toFixed(1)},${toY(v).toFixed(1)}`).join(' ');

  // Filled area path
  const areaPath = [
    `M ${toX(0).toFixed(1)},${(height - pad).toFixed(1)}`,
    ...values.map((v, i) => `L ${toX(i).toFixed(1)},${toY(v).toFixed(1)}`),
    `L ${toX(values.length - 1).toFixed(1)},${(height - pad).toFixed(1)}`,
    'Z',
  ].join(' ');

  // Threshold line Y coordinate
  const thresholdY = alertThreshold !== undefined
    ? toY(Math.max(alertThreshold, min))
    : null;

  const latestValue = values[values.length - 1];
  const isAlert = alertThreshold !== undefined && latestValue >= alertThreshold;

  return (
    <div className="flex flex-col gap-0.5">
      {(label || unit) && (
        <div className="flex justify-between items-center">
          {label && <span className="text-[10px] text-gray-500 font-mono uppercase tracking-wide">{label}</span>}
          <span className={`text-[11px] font-bold font-mono ${isAlert ? 'text-red-400' : 'text-orange-300'}`}>
            {latestValue.toFixed(2)}{unit ? ` ${unit}` : ''}
          </span>
        </div>
      )}
      <svg width={width} height={height} className="overflow-visible">
        {/* Area fill */}
        <path d={areaPath} fill={isAlert ? '#ef4444' : color} fillOpacity={0.12} />
        {/* Sparkline */}
        <polyline
          points={points}
          fill="none"
          stroke={isAlert ? '#ef4444' : color}
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Alert threshold dotted line */}
        {thresholdY !== null && thresholdY >= pad && thresholdY <= height - pad && (
          <line
            x1={pad}
            y1={thresholdY}
            x2={width - pad}
            y2={thresholdY}
            stroke="#ef4444"
            strokeWidth={1}
            strokeDasharray="3 2"
            opacity={0.7}
          />
        )}
        {/* Latest value dot */}
        <circle
          cx={toX(values.length - 1)}
          cy={toY(latestValue)}
          r={3}
          fill={isAlert ? '#ef4444' : color}
        />
      </svg>
    </div>
  );
}

interface ThreatBarProps {
  label: string;
  score: number;
  factors?: string[];
}

/**
 * Five-vector threat bar — single horizontal bar with score and label.
 */
export function ThreatBar({ label, score, factors = [] }: ThreatBarProps) {
  const color =
    score >= 70 ? '#ef4444' : score >= 45 ? '#f97316' : score >= 20 ? '#eab308' : '#22c55e';
  const bgColor =
    score >= 70 ? 'bg-red-500/20' : score >= 45 ? 'bg-orange-500/20' : score >= 20 ? 'bg-yellow-500/20' : 'bg-green-500/20';

  return (
    <div className="group relative">
      <div className="flex items-center gap-2 mb-0.5">
        <span className="text-[10px] text-gray-400 font-mono uppercase tracking-wider w-24 shrink-0">{label}</span>
        <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{ width: `${score}%`, backgroundColor: color }}
          />
        </div>
        <span className="text-[10px] font-bold font-mono w-8 text-right" style={{ color }}>
          {score.toFixed(0)}
        </span>
      </div>
      {factors.length > 0 && (
        <div className="absolute left-28 -top-0.5 z-20 hidden group-hover:block bg-gray-900 border border-gray-700 rounded p-2 shadow-xl max-w-xs">
          {factors.map((f, i) => (
            <p key={i} className="text-[10px] text-gray-300 mb-0.5 last:mb-0">• {f}</p>
          ))}
        </div>
      )}
    </div>
  );
}
