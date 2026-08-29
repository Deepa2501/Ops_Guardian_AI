import pytest
from python.governance.plan_manager import PlanManager
from python.governance.governed_invoker import governed_invoker
from python.governance.approval_manager import approval_manager
from python.database import get_db_context
from python.models import ProductionConfig


def test_human_approval_execution_lifecycle():
    """
    Test 3: Human Approval Flow
    HOLD -> APPROVE -> ArmorIQ Release -> GovernedInvoker executes -> SQLite load becomes 65%.
    """
    plan_manager = PlanManager()
    plan_capture, intent_token = plan_manager.create_maintenance_plan(
        "Monitor Production Unit A and autonomously create preventive maintenance work orders."
    )

    plan_id = intent_token.plan_id
    task_id = "TSK-TEST-APPROVAL-01"

    # 1. Action is held
    hold_result = governed_invoker.invoke(
        tool_name="set_production_load",
        arguments={"asset_id": "AST-01", "load_percent": 65},
        task_id=task_id,
        plan_id=plan_id,
    )
    action_id = hold_result["action_id"]

    # 2. Human Supervisor approves
    def execute_callback(tool_name, arguments, plan_id, action_id, delegation_id, reviewer):
        return governed_invoker.execute_approved_action(
            tool_name=tool_name,
            arguments=arguments,
            plan_id=plan_id,
            action_id=action_id,
            delegation_id=delegation_id,
            reviewer=reviewer,
        )

    approval_res = approval_manager.process_approval(
        action_id=action_id,
        reviewer="lead_engineer@opsguardian.ai",
        notes="Bearing thermal trip risk verified. Approved curtailment to 65%.",
        invoker_func=execute_callback,
    )

    assert approval_res["status"] == "success"
    assert approval_res["decision"] == "APPROVED"

    # 3. Verify real mutation in SQLite database
    with get_db_context() as db:
        cfg = db.query(ProductionConfig).filter(ProductionConfig.asset_id == "AST-01").first()
        assert cfg.load_percent == 65, "Database load should now be 65% after human approval"


def test_human_rejection_lifecycle():
    """
    Test 4: Human Rejection Flow
    HOLD -> REJECT -> ArmorIQ Block -> Tool execution cancelled -> SQLite load remains 100%.
    """
    plan_manager = PlanManager()
    plan_capture, intent_token = plan_manager.create_maintenance_plan(
        "Monitor Production Unit A and autonomously create preventive maintenance work orders."
    )

    plan_id = intent_token.plan_id
    task_id = "TSK-TEST-REJECTION-01"

    # 1. Action is held
    hold_result = governed_invoker.invoke(
        tool_name="set_production_load",
        arguments={"asset_id": "AST-01", "load_percent": 65},
        task_id=task_id,
        plan_id=plan_id,
    )
    action_id = hold_result["action_id"]

    # 2. Human Supervisor rejects
    rejection_res = approval_manager.process_rejection(
        action_id=action_id,
        reviewer="plant_manager@opsguardian.ai",
        reason="Reject curtailment: grid commitment demands 100% until standby train is online.",
    )

    assert rejection_res["status"] == "success"
    assert rejection_res["decision"] == "REJECTED"

    # 3. Verify SQLite database remains unchanged at 100%
    with get_db_context() as db:
        cfg = db.query(ProductionConfig).filter(ProductionConfig.asset_id == "AST-01").first()
        assert cfg.load_percent == 100, "Database load must remain 100% after rejection"
