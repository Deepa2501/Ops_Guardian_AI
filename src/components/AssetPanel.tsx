import React from 'react';
import { Activity, AlertTriangle, CheckCircle2, Cpu, Flame, Gauge } from 'lucide-react';
import { AssetData, TelemetryPoint, RiskEvaluation } from '../types';
import { Sparkline, ThreatBar } from './Charts';

interface AssetPanelProps {
  asset: AssetData;
  telemetry: TelemetryPoint[];
  risk?: RiskEvaluation;
  productionConfig?: { load_percent: number; safety_interlock: string };
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    OPERATIONAL: 'text-green-400 border-green-500/40 bg-green-500/10',
    WARNING: 'text-yellow-400 border-yellow-500/40 bg-yellow-500/10',
    DEGRADED: 'text-orange-400 border-orange-500/40 bg-orange-500/10',
    CRITICAL: 'text-red-400 border-red-500/40 bg-red-500/10',
    MAINTENANCE: 'text-blue-400 border-blue-500/40 bg-blue-500/10',
  };
  return (
    <span className={`text-[10px] font-bold border rounded px-2 py-0.5 font-mono ${map[status] ?? 'text-gray-400 border-gray-600 bg-gray-800'}`}>
      {status}
    </span>
  );
}

function RiskBadge({ level }: { level: string }) {
  const map: Record<string, string> = {
    CRITICAL: 'text-red-400 border-red-500/40 bg-red-500/10 animate-pulse',
    HIGH: 'text-orange-400 border-orange-500/40 bg-orange-500/10',
    MEDIUM: 'text-yellow-400 border-yellow-500/40 bg-yellow-500/10',
    LOW: 'text-green-400 border-green-500/40 bg-green-500/10',
  };
  return (
    <span className={`text-[10px] font-bold border rounded px-2 py-0.5 font-mono ${map[level] ?? 'text-gray-400 border-gray-600'}`}>
      ⚠ {level}
    </span>
  );
}

/**
 * Full asset panel: health metrics, sparklines, five-vector risk breakdown.
 */
export function AssetPanel({ asset, telemetry, risk, productionConfig }: AssetPanelProps) {
  const latest = telemetry.length > 0 ? telemetry[telemetry.length - 1] : null;
  const load = productionConfig?.load_percent ?? asset.load_percent;

  return (
    <div className="bg-gray-900/60 border border-gray-700 rounded-xl p-5 space-y-5">
      {/* Asset Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Cpu className="text-orange-400" size={16} />
            <span className="text-white font-bold text-sm font-mono">{asset.id}</span>
            <StatusBadge status={asset.status} />
            {risk && <RiskBadge level={risk.risk_level} />}
          </div>
          <p className="text-gray-400 text-xs">{asset.name}</p>
          <p className="text-gray-600 text-[10px] font-mono">{asset.location}</p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-orange-400 font-mono">
            {risk ? risk.risk_score.toFixed(0) : asset.health_score.toFixed(0)}
          </div>
          <div className="text-[10px] text-gray-500 font-mono">
            {risk ? 'RISK SCORE' : 'HEALTH SCORE'}
          </div>
        </div>
      </div>

      {/* Key Metrics Row */}
      <div className="grid grid-cols-4 gap-3">
        <MetricCard
          label="Vibration"
          value={latest?.vibration_mms?.toFixed(2) ?? asset.vibration_mms?.toFixed(2)}
          unit="mm/s"
          alert={latest?.vibration_mms !== undefined && latest.vibration_mms > 4.5}
          icon={<Activity size={12} />}
        />
        <MetricCard
          label="Temperature"
          value={latest?.temperature_c?.toFixed(1) ?? asset.temperature_c?.toFixed(1)}
          unit="°C"
          alert={latest?.temperature_c !== undefined && latest.temperature_c > 80}
          icon={<Flame size={12} />}
        />
        <MetricCard
          label="Lube Pressure"
          value={latest?.pressure_bar?.toFixed(2) ?? asset.pressure_bar?.toFixed(2)}
          unit="bar"
          alert={latest?.pressure_bar !== undefined && latest.pressure_bar < 2.0}
          icon={<Gauge size={12} />}
        />
        <MetricCard
          label="Load"
          value={`${load}`}
          unit="%"
          alert={load >= 100}
          icon={<CheckCircle2 size={12} />}
        />
      </div>

      {/* Telemetry Sparklines */}
      {telemetry.length > 2 && (
        <div className="grid grid-cols-3 gap-4">
          <Sparkline data={telemetry} field="vibration_mms" label="Vibration" unit="mm/s"
            alertThreshold={4.5} color="#f97316" width={150} height={52} />
          <Sparkline data={telemetry} field="temperature_c" label="Temperature" unit="°C"
            alertThreshold={80} color="#ef4444" width={150} height={52} />
          <Sparkline data={telemetry} field="pressure_bar" label="Pressure" unit="bar"
            color="#3b82f6" width={150} height={52} />
        </div>
      )}

      {/* Five-Vector Risk Breakdown */}
      {risk?.threat_vectors && (
        <div className="border-t border-gray-700 pt-4 space-y-1.5">
          <p className="text-[10px] text-gray-500 font-mono uppercase tracking-widest mb-2">
            Five-Vector Risk Breakdown
          </p>
          {Object.entries(risk.threat_vectors).map(([key, vec]) => (
            <ThreatBar
              key={key}
              label={key.replace('_', ' ')}
              score={vec.score}
              factors={vec.factors}
            />
          ))}
          <div className="mt-2 bg-gray-900/50 border border-gray-700 rounded p-2.5 text-[11px] text-gray-300">
            <span className="text-orange-400 font-semibold">Recommended: </span>
            {risk.recommended_action}
          </div>
          {risk.iso_10816_zone && (
            <p className="text-[10px] text-gray-500 font-mono">
              ISO 10816: <span className={`font-bold ${risk.iso_10816_zone.includes('D') ? 'text-red-400' : risk.iso_10816_zone.includes('C') ? 'text-orange-400' : 'text-gray-400'}`}>
                {risk.iso_10816_zone}
              </span>
              {' · '}
              Failure Prob 24h: <span className="text-orange-300 font-bold">{risk.failure_probability_24h?.toFixed(1)}%</span>
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function MetricCard({
  label, value, unit, alert, icon,
}: {
  label: string; value: string | number | undefined; unit: string; alert?: boolean; icon?: React.ReactNode;
}) {
  return (
    <div className={`rounded-lg p-3 border ${alert ? 'border-red-500/50 bg-red-900/20' : 'border-gray-700 bg-gray-800/50'}`}>
      <div className="flex items-center gap-1 mb-1">
        <span className={alert ? 'text-red-400' : 'text-gray-500'}>{icon}</span>
        <span className="text-[9px] text-gray-500 font-mono uppercase tracking-wider">{label}</span>
      </div>
      <div className={`text-lg font-bold font-mono ${alert ? 'text-red-400' : 'text-white'}`}>
        {value ?? '—'}
        <span className="text-[10px] text-gray-500 ml-0.5">{unit}</span>
      </div>
    </div>
  );
}
