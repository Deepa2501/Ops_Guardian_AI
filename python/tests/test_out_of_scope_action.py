import pytest
from python.governance.plan_manager import PlanManager
from python.governance.governed_invoker import governed_invoker
from python.database import get_db_context
from python.models import ProductionConfig
from python.governance.approval_manager import approval_manager


def test_out_of_scope_action_hold():
    """
    Test 2: Out-of-Scope Action Interception
    capture_plan -> set_production_load -> ArmorIQ HOLD -> Tool does NOT execute -> SQLite remains 100%.
    """
    plan_manager = PlanManager()
    plan_capture, intent_token = plan_manager.create_maintenance_plan(
        "Monitor Production Unit A and autonomously create preventive maintenance work orders."
    )

    plan_id = intent_token.plan_id
    task_id = "TSK-TEST-OUTOFSCOPE-01"

    # Verify initial database state: Load = 100%
    with get_db_context() as db:
        cfg = db.query(ProductionConfig).filter(ProductionConfig.asset_id == "AST-01").first()
        assert cfg is not None
        assert cfg.load_percent == 100

    # Agent attempts consequential operational tool 'set_production_load'
    # Note: 'set_production_load' is an operational function, not a keyword-flagged dangerous name
    result = governed_invoker.invoke(
        tool_name="set_production_load",
        arguments={"asset_id": "AST-01", "load_percent": 65},
        task_id=task_id,
        plan_id=plan_id,
    )

    # ArmorIQ Governance Assertions
    assert result["authorized"] is False
    assert result["armoriq_decision"] == "HOLD"
    assert result["status"] == "HELD"
    assert result["execution_status"] == "NOT_EXECUTED"
    assert "delegation_id" in result
    assert "action_id" in result

    # CRITICAL SECURITY VERIFICATION: Tool did NOT execute and SQLite database remained UNCHANGED at 100%
    with get_db_context() as db:
        cfg_after = db.query(ProductionConfig).filter(ProductionConfig.asset_id == "AST-01").first()
        assert cfg_after.load_percent == 100, "Security Violation: Database mutated before human approval!"

    # Verify approval manager has registered the pending hold
    pending = approval_manager.get_approval(result["action_id"])
    assert pending is not None
    assert pending["status"] == "PENDING_APPROVAL"
    assert pending["tool_name"] == "set_production_load"
    assert pending["arguments"]["load_percent"] == 65
