"""
test_risk_engine.py — Tests for the five-vector deterministic risk engine.
"""
import pytest
from python.services.risk_engine import RiskEngine, risk_engine


def test_critical_risk_all_vectors():
    """CRITICAL condition: high vibration + high temp + low pressure at full load."""
    result = risk_engine.calculate_asset_risk(
        vibration_mms=7.82,
        temperature_c=88.5,
        pressure_bar=1.85,
        rpm=4740,
        load_percent=100,
    )
    assert result["risk_level"] == "CRITICAL"
    assert result["risk_score"] >= 70.0  # CRITICAL threshold is 70.0
    assert "mechanical" in result["threat_vectors"]
    assert "thermal" in result["threat_vectors"]
    assert "lubrication" in result["threat_vectors"]
    assert "production_stress" in result["threat_vectors"]
    assert "sensor_anomaly" in result["threat_vectors"]
    assert result["threat_vectors"]["mechanical"]["score"] > 50
    assert result["threat_vectors"]["thermal"]["score"] > 50
    assert result["threat_vectors"]["lubrication"]["score"] > 30


def test_normal_risk_low():
    """NORMAL condition should produce LOW risk."""
    result = risk_engine.calculate_asset_risk(
        vibration_mms=1.8,
        temperature_c=60.0,
        pressure_bar=2.42,
        rpm=4800,
        load_percent=75,
    )
    assert result["risk_level"] == "LOW"
    assert result["risk_score"] < 25.0


def test_mechanical_vector_iso10816():
    """Validates ISO 10816 zone classification."""
    result_zone_d = risk_engine.calculate_asset_risk(7.5, 70, 2.3, 4800, 80)
    assert result_zone_d["threat_vectors"]["mechanical"]["iso_10816_zone"] == "Zone D (Unacceptable)"

    result_zone_c = risk_engine.calculate_asset_risk(5.0, 70, 2.3, 4800, 80)
    assert result_zone_c["threat_vectors"]["mechanical"]["iso_10816_zone"] == "Zone C (Restricted)"

    result_zone_a = risk_engine.calculate_asset_risk(1.5, 60, 2.4, 4800, 70)
    assert result_zone_a["threat_vectors"]["mechanical"]["iso_10816_zone"] == "Zone A (Good)"


def test_risk_score_bounded():
    """Risk score must never exceed 100."""
    result = risk_engine.calculate_asset_risk(15.0, 150.0, 0.5, 0, 100)
    assert result["risk_score"] <= 100.0
    assert result["risk_score"] >= 0.0


def test_all_five_vectors_present():
    """All five threat vectors must always be present in output."""
    result = risk_engine.calculate_asset_risk(3.0, 65, 2.3, 4800, 80)
    vectors = result["threat_vectors"]
    for v in ["mechanical", "thermal", "lubrication", "production_stress", "sensor_anomaly"]:
        assert v in vectors
        assert "score" in vectors[v]
        assert "factors" in vectors[v]


def test_recommended_action_present():
    result = risk_engine.calculate_asset_risk(7.82, 88.5, 1.85, 4740, 100)
    assert "recommended_action" in result
    assert len(result["recommended_action"]) > 5


def test_confidence_in_range():
    result = risk_engine.calculate_asset_risk(7.82, 88.5, 1.85, 4740, 100)
    assert 0.0 <= result["confidence"] <= 1.0
