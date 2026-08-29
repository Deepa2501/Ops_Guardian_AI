import React from 'react';
import { Zap, Square } from 'lucide-react';

const SCENARIOS = [
  { id: 'NORMAL', label: 'Normal', color: 'text-green-400', desc: 'Steady-state operation' },
  { id: 'VIBRATION_RISE', label: 'Vibration Rise', color: 'text-yellow-400', desc: 'Bearing wear progression' },
  { id: 'THERMAL_RUNAWAY', label: 'Thermal Runaway', color: 'text-orange-400', desc: 'Rapidly rising temp + vib' },
  { id: 'LOW_LUBE_PRESSURE', label: 'Low Lube', color: 'text-red-400', desc: 'Lube oil pressure drop' },
  { id: 'COMBINED_BEARING_FAILURE', label: 'Bearing Failure', color: 'text-red-600', desc: 'All indicators critical' },
];

interface SimulatorControlsProps {
  activeScenario?: string | null;
  onSetScenario: (scenario: string) => void;
  onStop: () => void;
  onAdvanceTick: () => void;
  ticks?: number;
  isRunning?: boolean;
}

/**
 * Telemetry simulator controls panel.
 * Allows selecting and activating different industrial failure scenarios.
 */
export function SimulatorControls({
  activeScenario,
  onSetScenario,
  onStop,
  onAdvanceTick,
  ticks = 0,
  isRunning = false,
}: SimulatorControlsProps) {
  return (
    <div className="bg-gray-900/60 border border-gray-700 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-bold text-white font-mono">Telemetry Simulator</p>
          <p className="text-[10px] text-gray-500 font-mono">
            Inject industrial failure scenarios for testing
          </p>
        </div>
        {activeScenario && (
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-gray-500 font-mono">ticks: {ticks}</span>
            <button
              onClick={onAdvanceTick}
              className="flex items-center gap-1 text-[10px] font-mono bg-orange-900/40 hover:bg-orange-900/70 border border-orange-500/40 text-orange-400 rounded px-2 py-1 transition"
            >
              <Zap size={10} />
              Tick
            </button>
            <button
              onClick={onStop}
              className="flex items-center gap-1 text-[10px] font-mono bg-gray-800 hover:bg-gray-700 border border-gray-600 text-gray-400 rounded px-2 py-1 transition"
            >
              <Square size={10} />
              Stop
            </button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-5 gap-2">
        {SCENARIOS.map((s) => (
          <button
            key={s.id}
            onClick={() => onSetScenario(s.id)}
            title={s.desc}
            className={`rounded-lg border p-2 text-left transition-all hover:scale-[1.02] ${
              activeScenario === s.id
                ? 'border-orange-500/60 bg-orange-900/20'
                : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
            }`}
          >
            <p className={`text-[10px] font-bold font-mono ${activeScenario === s.id ? s.color : 'text-gray-400'}`}>
              {s.label}
            </p>
            <p className="text-[9px] text-gray-600 mt-0.5 leading-tight">{s.desc}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
