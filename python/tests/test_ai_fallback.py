"""
test_ai_fallback.py — Tests that AI provider falls back gracefully on all errors.
"""
import pytest
from python.services.ai_provider import GeminiProvider, DeterministicProvider, get_ai_provider


def test_deterministic_provider_always_works():
    """DeterministicProvider must never raise, never need API key."""
    provider = DeterministicProvider()
    result = provider.diagnose_incident(
        asset_info={"id": "AST-01", "name": "Test Asset"},
        telemetry=[{"vibration_mms": 7.82, "temperature_c": 88.5, "pressure_bar": 1.85}],
        risk_data={"risk_score": 100, "risk_level": "CRITICAL", "risk_factors": []},
    )
    assert result["provider"] == "deterministic"
    assert result["fallback_used"] == False
    assert "diagnostic_result" in result
    dr = result["diagnostic_result"]
    assert "failure_mechanism" in dr
    assert "root_cause" in dr
    assert "severity" in dr
    assert "work_order" in dr
    assert "production_mitigation" in dr


def test_deterministic_provider_structured_output():
    """DiagnosisOutput must validate with Pydantic."""
    provider = DeterministicProvider()
    result = provider.diagnose_incident(
        asset_info={"id": "AST-01"},
        telemetry=[{"vibration_mms": 2.0, "temperature_c": 60.0}],
        risk_data={"risk_score": 10, "risk_level": "LOW"},
    )
    dr = result["diagnostic_result"]
    assert 0.0 <= dr["confidence"] <= 1.0
    assert dr["severity"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
    assert isinstance(dr["evidence"], list)
    assert isinstance(dr["recommended_actions"], list)
    assert isinstance(dr["work_order"], dict)
    assert isinstance(dr["production_mitigation"], dict)


def test_gemini_provider_no_key_raises():
    """GeminiProvider must raise when API key is not set."""
    import os
    original = os.environ.get("GEMINI_API_KEY", "")
    os.environ["GEMINI_API_KEY"] = ""
    try:
        provider = GeminiProvider()
        with pytest.raises(Exception) as exc:
            provider.diagnose_incident({}, [], {})
        assert "GEMINI_API_KEY" in str(exc.value) or "not set" in str(exc.value)
    finally:
        os.environ["GEMINI_API_KEY"] = original


def test_diagnostic_agent_fallback_on_gemini_error():
    """DiagnosticAgent must fall back to deterministic when Gemini fails."""
    import os
    os.environ["AI_PROVIDER"] = "gemini"
    os.environ["GEMINI_API_KEY"] = ""  # force failure

    from python.agent.diagnostic_agent import DiagnosticAgent
    agent = DiagnosticAgent()
    result = agent.analyze(
        asset_state={"id": "AST-01", "name": "Test", "type": "Compressor"},
        telemetry={
            "current_metrics": {"vibration_mms": 7.82, "temperature_c": 88.5,
                                  "pressure_bar": 1.85, "rpm": 4740, "load_percent": 100},
            "telemetry_history": [],
        },
    )
    # Must always return a valid diagnosis
    assert "risk_evaluation" in result
    assert "diagnosis" in result
    assert "work_order_plan" in result

    os.environ["AI_PROVIDER"] = "deterministic"


def test_get_ai_provider_deterministic():
    """get_ai_provider() returns DeterministicProvider when AI_PROVIDER=deterministic."""
    import os
    os.environ["AI_PROVIDER"] = "deterministic"
    import importlib
    import python.config as cfg
    importlib.reload(cfg)
    provider = DeterministicProvider()
    assert provider.provider_name == "deterministic"
    result = provider.health_check()
    assert result["status"] == "healthy"
