import pytest
from python.governance.plan_manager import PlanManager
from python.governance.governed_invoker import governed_invoker
from python.database import get_db_context
from python.models import WorkOrder


def test_authorized_action_execution():
    """
    Test 1: Authorized Action Lifecycle
    capture_plan -> create_work_order -> ArmorIQ ALLOW -> tool executes -> SQLite record created.
    """
    plan_manager = PlanManager()
    plan_capture, intent_token = plan_manager.create_maintenance_plan(
        "Monitor Production Unit A and create preventive maintenance work orders."
    )

    plan_id = intent_token.plan_id
    task_id = "TSK-TEST-AUTH-01"

    # Invocation of authorized tool 'create_work_order'
    result = governed_invoker.invoke(
        tool_name="create_work_order",
        arguments={
            "asset_id": "AST-01",
            "title": "Emergency Stage-2 Bearing Vibration Inspection",
            "priority": "P1",
            "description": "Peak vibration 7.82 mm/s exceeds ISO 10816 Zone D limits.",
        },
        task_id=task_id,
        plan_id=plan_id,
    )

    # Assertions on ArmorIQ verification
    assert result["authorized"] is True
    assert result["armoriq_decision"] == "ALLOW"
    assert result["status"] == "EXECUTED"
    assert "work_order_id" in result["result"]

    wo_id = result["result"]["work_order_id"]

    # Verify persistent state change in SQLite database
    with get_db_context() as db:
        wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
        assert wo is not None
        assert wo.asset_id == "AST-01"
        assert wo.priority == "P1"
        assert wo.title == "Emergency Stage-2 Bearing Vibration Inspection"
        assert wo.status == "CREATED"
