"""
test_armoriq_adapter.py — Tests for ArmorIQ adapter mock/disabled modes.
"""
import pytest
from python.governance.armoriq_adapter import ArmorIQAdapter


def _make_mock_adapter():
    return ArmorIQAdapter(mode="mock")


def _make_disabled_adapter():
    return ArmorIQAdapter(mode="disabled")


# ── Mock mode tests ───────────────────────────────────────────────────────────

def test_mock_capture_plan_returns_token():
    adapter = _make_mock_adapter()
    plan_capture, token = adapter.capture_authorized_plan(
        task_goal="Monitor asset",
        authorized_tools=["read_telemetry", "create_work_order"],
    )
    assert plan_capture is None  # no real SDK in mock
    assert token is not None
    assert token.plan_id.startswith("plan-mock-")
    assert len(token.plan_hash) == 64
    assert token.total_steps == 2
    assert "read_telemetry" in token.authorized_tools


def test_mock_allow_for_authorized_tool():
    adapter = _make_mock_adapter()
    _, token = adapter.capture_authorized_plan("test", ["read_telemetry"])
    result = adapter.verify_action_authorization(token.plan_id, "read_telemetry", {})
    assert result["decision"] == "ALLOW"
    assert result["allowed"] is True


def test_mock_hold_for_unauthorized_tool():
    adapter = _make_mock_adapter()
    _, token = adapter.capture_authorized_plan("test", ["read_telemetry"])
    result = adapter.verify_action_authorization(token.plan_id, "set_production_load", {"load_percent": 65})
    assert result["decision"] == "HOLD"
    assert result["allowed"] is False
    assert result["delegation_id"] is not None
    assert result["delegation_id"].startswith("delg-mock-")


def test_mock_block_for_unknown_plan():
    adapter = _make_mock_adapter()
    result = adapter.verify_action_authorization("plan-nonexistent", "read_telemetry", {})
    assert result["decision"] == "BLOCK"
    assert result["allowed"] is False


def test_mock_delegation_release():
    adapter = _make_mock_adapter()
    _, token = adapter.capture_authorized_plan("test", ["read_telemetry"])
    hold = adapter.verify_action_authorization(token.plan_id, "set_production_load", {})
    delegation_id = hold["delegation_id"]

    released = adapter.release_delegation(delegation_id, "approved")
    assert released is not None
    assert released["status"] == "approved"


# ── Disabled mode tests ───────────────────────────────────────────────────────

def test_disabled_allows_read_only():
    adapter = _make_disabled_adapter()
    _, token = adapter.capture_authorized_plan("test", ["read_telemetry"])
    result = adapter.verify_action_authorization(token.plan_id, "read_telemetry", {})
    # Disabled mode uses _disabled_verify which checks action_policy
    assert result["decision"] == "ALLOW"
    assert result["allowed"] is True


def test_disabled_blocks_consequential():
    adapter = _make_disabled_adapter()
    _, token = adapter.capture_authorized_plan("test", ["set_production_load"])
    result = adapter.verify_action_authorization(token.plan_id, "set_production_load", {})
    assert result["decision"] == "BLOCK"
    assert result["allowed"] is False
    assert "ARMORIQ_MODE=disabled" in result["reason"]


def test_disabled_blocks_work_order_write():
    adapter = _make_disabled_adapter()
    _, token = adapter.capture_authorized_plan("test", ["create_work_order"])
    result = adapter.verify_action_authorization(token.plan_id, "create_work_order", {})
    # create_work_order is LOW_RISK_WRITE — blocked in disabled mode
    assert result["decision"] == "BLOCK"


def test_mode_reported_correctly():
    mock = _make_mock_adapter()
    assert mock.get_mode() == "mock"

    disabled = _make_disabled_adapter()
    assert disabled.get_mode() == "disabled"
