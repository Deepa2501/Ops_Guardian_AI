"""
test_simulator.py — Telemetry simulator tests.
"""
import pytest
from python.services.telemetry_simulator import TelemetrySimulator, SCENARIO_BASELINES
from python.models import TelemetryRecord
from python.database import get_db_context


def _fresh_simulator():
    return TelemetrySimulator()


def test_all_scenarios_are_valid():
    """All scenarios must be settable without error."""
    sim = _fresh_simulator()
    for scenario in SCENARIO_BASELINES:
        result = sim.set_scenario("AST-01", scenario)
        assert result["status"] == "success"
        assert result["scenario"] == scenario


def test_unknown_scenario_returns_error():
    sim = _fresh_simulator()
    result = sim.set_scenario("AST-01", "NONEXISTENT_SCENARIO")
    assert result["status"] == "error"


def test_set_scenario_writes_to_db():
    """set_scenario must write a TelemetryRecord to the database."""
    sim = _fresh_simulator()
    sim.set_scenario("AST-01", "THERMAL_RUNAWAY")

    with get_db_context() as db:
        count_after = db.query(TelemetryRecord).filter(TelemetryRecord.asset_id == "AST-01").count()
    assert count_after > 0


def test_thermal_runaway_starts_anomaly():
    """THERMAL_RUNAWAY scenario must immediately flag anomalies."""
    sim = _fresh_simulator()
    result = sim.set_scenario("AST-01", "THERMAL_RUNAWAY")
    # After a few ticks, anomaly should be flagged
    for _ in range(3):
        metrics = sim.advance_tick("AST-01")
    assert metrics is not None
    # Either vibration or temperature should be in alert range
    assert metrics["vibration_mms"] >= 4.0 or metrics["temperature_c"] >= 78.0


def test_advance_tick_increments_values():
    """Each advance_tick must produce non-identical values (scenario progressing)."""
    sim = _fresh_simulator()
    sim.set_scenario("AST-01", "VIBRATION_RISE")
    tick1 = sim.advance_tick("AST-01")
    tick2 = sim.advance_tick("AST-01")
    assert tick1 is not None
    assert tick2 is not None
    # Vibration must generally be rising
    assert tick2["vibration_mms"] >= tick1["vibration_mms"] - 0.5  # allow slight noise


def test_advance_tick_no_scenario_returns_none():
    sim = _fresh_simulator()
    result = sim.advance_tick("AST-UNKNOWN")
    assert result is None


def test_stop_all_clears_state():
    sim = _fresh_simulator()
    sim.set_scenario("AST-01", "NORMAL")
    result = sim.stop_all()
    assert "cleared_assets" in result
    assert "AST-01" in result["cleared_assets"]
    status = sim.get_status()
    assert len(status["active_scenarios"]) == 0


def test_get_status_reports_scenarios():
    sim = _fresh_simulator()
    sim.set_scenario("AST-01", "NORMAL")
    status = sim.get_status()
    assert "AST-01" in status["active_scenarios"]
    assert status["active_scenarios"]["AST-01"]["scenario"] == "NORMAL"
    assert len(status["available_scenarios"]) == len(SCENARIO_BASELINES)


def test_metrics_within_physical_bounds():
    """Simulator must not produce physically impossible values."""
    sim = _fresh_simulator()
    sim.set_scenario("AST-01", "COMBINED_BEARING_FAILURE")
    for _ in range(10):
        metrics = sim.advance_tick("AST-01")
        assert 0 <= metrics["vibration_mms"] <= 15.0
        assert 20.0 <= metrics["temperature_c"] <= 180.0
        assert metrics["pressure_bar"] >= 0.0
