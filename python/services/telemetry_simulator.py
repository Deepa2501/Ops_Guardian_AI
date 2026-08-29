"""
Telemetry Simulator
Generates realistic high-frequency sensor data for demo scenarios.
Does NOT interact with real industrial control systems.
"""
import random
import datetime
import logging
from typing import Dict, Any, Optional

from python.database import get_db_context
from python.models import TelemetryRecord

logger = logging.getLogger("opsguardian.services.simulator")

# ── Scenario definitions ──────────────────────────────────────────────────────

SCENARIO_BASELINES = {
    "NORMAL": {
        "vibration_mms": 2.1,
        "temperature_c": 62.0,
        "pressure_bar": 2.42,
        "rpm": 4800,
        "load_percent": 80,
        "vib_delta": 0.05,
        "temp_delta": 0.2,
        "press_delta": -0.01,
        "anomaly_threshold_vib": 99.0,  # never anomaly in normal
        "anomaly_threshold_temp": 99.0,
        "description": "Normal steady-state operation",
    },
    "VIBRATION_RISE": {
        "vibration_mms": 3.5,
        "temperature_c": 70.0,
        "pressure_bar": 2.25,
        "rpm": 4800,
        "load_percent": 90,
        "vib_delta": 0.35,
        "temp_delta": 0.5,
        "press_delta": -0.02,
        "anomaly_threshold_vib": 4.5,
        "anomaly_threshold_temp": 82.0,
        "description": "Increasing vibration — bearing wear progression",
    },
    "THERMAL_RUNAWAY": {
        "vibration_mms": 4.5,
        "temperature_c": 78.0,
        "pressure_bar": 2.10,
        "rpm": 4760,
        "load_percent": 100,
        "vib_delta": 0.9,
        "temp_delta": 3.5,
        "press_delta": -0.035,
        "anomaly_threshold_vib": 4.5,
        "anomaly_threshold_temp": 78.0,
        "description": "Thermal runaway — rapidly rising temperature and vibration",
    },
    "LOW_LUBE_PRESSURE": {
        "vibration_mms": 5.2,
        "temperature_c": 82.0,
        "pressure_bar": 2.05,
        "rpm": 4750,
        "load_percent": 95,
        "vib_delta": 0.15,
        "temp_delta": 0.8,
        "press_delta": -0.055,
        "anomaly_threshold_vib": 4.5,
        "anomaly_threshold_temp": 80.0,
        "description": "Lube oil pressure dropping — filter blockage or pump degradation",
    },
    "COMBINED_BEARING_FAILURE": {
        "vibration_mms": 6.8,
        "temperature_c": 90.0,
        "pressure_bar": 1.82,
        "rpm": 4720,
        "load_percent": 100,
        "vib_delta": 1.2,
        "temp_delta": 4.5,
        "press_delta": -0.04,
        "anomaly_threshold_vib": 4.5,
        "anomaly_threshold_temp": 80.0,
        "description": "Combined bearing failure — all indicators critical, imminent seizure",
    },
}


class TelemetrySimulator:
    """
    Generates realistic industrial telemetry for demo/testing scenarios.
    Each `set_scenario()` call immediately writes a telemetry record to the DB.
    Stateful: tracks current values per asset as scenario progresses.
    """

    def __init__(self):
        self._active_scenarios: Dict[str, str] = {}   # asset_id -> scenario_name
        self._current_values: Dict[str, Dict[str, Any]] = {}  # asset_id -> current metrics
        self._tick_counts: Dict[str, int] = {}
        self._running: bool = False

    def set_scenario(self, asset_id: str, scenario: str) -> Dict[str, Any]:
        """Set active scenario for asset and write first telemetry tick to DB."""
        if scenario not in SCENARIO_BASELINES:
            return {
                "status": "error",
                "message": f"Unknown scenario '{scenario}'. Valid: {list(SCENARIO_BASELINES.keys())}",
            }

        baseline = SCENARIO_BASELINES[scenario]
        self._active_scenarios[asset_id] = scenario
        self._tick_counts[asset_id] = 0

        # Initialize current values from baseline with small noise
        self._current_values[asset_id] = {
            "vibration_mms": baseline["vibration_mms"] + random.gauss(0, 0.05),
            "temperature_c": baseline["temperature_c"] + random.gauss(0, 0.3),
            "pressure_bar": baseline["pressure_bar"] + random.gauss(0, 0.02),
            "rpm": baseline["rpm"] + random.gauss(0, 10),
            "load_percent": baseline["load_percent"],
        }

        # Write first tick to DB immediately
        metrics = self._generate_tick(asset_id, scenario)
        self._write_telemetry(asset_id, metrics)

        logger.info("Scenario set: asset=%s scenario=%s", asset_id, scenario)
        return {
            "status": "success",
            "asset_id": asset_id,
            "scenario": scenario,
            "description": baseline["description"],
            "initial_metrics": metrics,
        }

    def advance_tick(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Advance the scenario by one tick, write to DB, return new metrics."""
        scenario = self._active_scenarios.get(asset_id)
        if not scenario:
            return None
        metrics = self._generate_tick(asset_id, scenario)
        self._write_telemetry(asset_id, metrics)
        return metrics

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "active_scenarios": {
                k: {"scenario": v, "ticks": self._tick_counts.get(k, 0)}
                for k, v in self._active_scenarios.items()
            },
            "available_scenarios": list(SCENARIO_BASELINES.keys()),
        }

    def stop_all(self) -> Dict[str, Any]:
        self._running = False
        cleared = list(self._active_scenarios.keys())
        self._active_scenarios.clear()
        self._current_values.clear()
        self._tick_counts.clear()
        return {"status": "stopped", "cleared_assets": cleared}

    # ── Internal helpers ──────────────────────────────────────────────────

    def _generate_tick(self, asset_id: str, scenario: str) -> Dict[str, Any]:
        baseline = SCENARIO_BASELINES[scenario]
        tick = self._tick_counts.get(asset_id, 0)
        self._tick_counts[asset_id] = tick + 1

        cv = self._current_values.get(asset_id, {
            "vibration_mms": baseline["vibration_mms"],
            "temperature_c": baseline["temperature_c"],
            "pressure_bar": baseline["pressure_bar"],
            "rpm": baseline["rpm"],
            "load_percent": baseline["load_percent"],
        })

        # Progress scenario values forward with noise
        noise = lambda sigma: random.gauss(0, sigma)
        new_vib = cv["vibration_mms"] + baseline["vib_delta"] + noise(0.08)
        new_temp = cv["temperature_c"] + baseline["temp_delta"] + noise(0.4)
        new_press = max(0.5, cv["pressure_bar"] + baseline["press_delta"] + noise(0.01))
        new_rpm = cv["rpm"] + noise(15)
        load = baseline["load_percent"]

        # Clamp vibration — physical sensors saturate around 15 mm/s
        new_vib = max(0.1, min(new_vib, 15.0))
        new_temp = max(20.0, min(new_temp, 180.0))

        anomaly = (
            new_vib >= baseline["anomaly_threshold_vib"]
            or new_temp >= baseline["anomaly_threshold_temp"]
            or new_press <= 1.85
        )

        summary = f"{scenario}: vib={new_vib:.2f} mm/s, temp={new_temp:.1f}°C, press={new_press:.2f} bar"

        metrics = {
            "vibration_mms": round(new_vib, 3),
            "temperature_c": round(new_temp, 2),
            "pressure_bar": round(new_press, 3),
            "rpm": round(new_rpm, 0),
            "load_percent": load,
            "anomaly_flag": anomaly,
            "metric_summary": summary,
        }

        # Update current values for next tick
        self._current_values[asset_id] = {
            "vibration_mms": new_vib,
            "temperature_c": new_temp,
            "pressure_bar": new_press,
            "rpm": new_rpm,
            "load_percent": load,
        }

        return metrics

    def _write_telemetry(self, asset_id: str, metrics: Dict[str, Any]) -> None:
        """Write a TelemetryRecord to the database."""
        try:
            with get_db_context() as db:
                record = TelemetryRecord(
                    asset_id=asset_id,
                    timestamp=datetime.datetime.utcnow(),
                    vibration_mms=metrics["vibration_mms"],
                    temperature_c=metrics["temperature_c"],
                    pressure_bar=metrics["pressure_bar"],
                    rpm=float(metrics["rpm"]),
                    load_percent=int(metrics["load_percent"]),
                    anomaly_flag=metrics["anomaly_flag"],
                    metric_summary=metrics["metric_summary"],
                )
                db.add(record)
                db.commit()
        except Exception as e:
            logger.error("Failed to write telemetry tick: %s", e)


# Global Singleton
telemetry_simulator = TelemetrySimulator()
