"""
test_unknown_tool_blocked.py — Unknown tools must ALWAYS be BLOCKED.
CRITICAL: These tests must ALWAYS pass. Failure = security regression.
"""
import pytest
from python.governance.governed_invoker import GovernedInvoker
from python.governance.action_policy import get_tool_risk_level, ActionRiskLevel, is_known_tool


def _make_invoker_with_plan():
    """Returns a GovernedInvoker and a valid plan_id."""
    from python.governance.armoriq_adapter import ArmorIQAdapter
    adapter = ArmorIQAdapter(mode="mock")
    _, token = adapter.capture_authorized_plan(
        task_goal="test",
        authorized_tools=["read_telemetry"],
    )
    invoker = GovernedInvoker()
    invoker.engine = adapter
    return invoker, token.plan_id


def test_unknown_tool_blocked_immediately():
    """Unknown tool must return BLOCKED without any execution attempt."""
    invoker, plan_id = _make_invoker_with_plan()
    result = invoker.invoke(
        tool_name="delete_all_assets",  # completely unknown
        arguments={"evil": True},
        task_id="task-test",
        plan_id=plan_id,
    )
    assert result["status"] == "BLOCKED"
    assert result["armoriq_decision"] == "BLOCK"
    assert result["authorized"] is False


def test_unknown_tool_not_in_policy():
    """Unregistered tools must not appear in TOOL_POLICY."""
    assert not is_known_tool("hack_the_planet")
    assert not is_known_tool("rm_rf_slash")
    assert not is_known_tool("delete_all_assets")
    assert not is_known_tool("")


def test_unknown_tool_defaults_to_critical_control():
    """Unknown tools must default to CRITICAL_CONTROL (most restrictive)."""
    level = get_tool_risk_level("some_unknown_tool")
    assert level == ActionRiskLevel.CRITICAL_CONTROL


def test_known_read_tools_are_read_only():
    assert get_tool_risk_level("read_telemetry") == ActionRiskLevel.READ_ONLY
    assert get_tool_risk_level("read_asset_state") == ActionRiskLevel.READ_ONLY
    assert is_known_tool("read_telemetry")


def test_critical_tools_classified_correctly():
    assert get_tool_risk_level("set_production_load") == ActionRiskLevel.CRITICAL_CONTROL
    assert get_tool_risk_level("modify_safety_interlock") == ActionRiskLevel.CRITICAL_CONTROL


def test_work_order_tools_low_risk():
    assert get_tool_risk_level("create_work_order") == ActionRiskLevel.LOW_RISK_WRITE
    assert get_tool_risk_level("assign_work_order") == ActionRiskLevel.LOW_RISK_WRITE


def test_unknown_tool_not_in_authorized_plan_still_blocked():
    """Even if ARMORIQ says ALLOW, unknown tools must be blocked by policy first."""
    invoker, plan_id = _make_invoker_with_plan()
    # Inject "allow" decision from adapter, but tool is unknown
    from python.governance.armoriq_adapter import ArmorIQAdapter
    adapter = ArmorIQAdapter(mode="mock")
    # Manually add evil tool to mock token to simulate ALLOW
    adapter._mock_tokens[plan_id] = {
        "tools": ["delete_all_assets"],
        "plan_hash": "fakehash",
        "plan": {"steps": [{"step": 1, "action": "delete_all_assets"}]}
    }
    invoker.engine = adapter
    result = invoker.invoke(
        tool_name="delete_all_assets",
        arguments={},
        task_id="task-test",
        plan_id=plan_id,
    )
    # Must be blocked by action_policy check before ArmorIQ
    assert result["status"] == "BLOCKED"
