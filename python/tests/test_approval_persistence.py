"""
test_approval_persistence.py — Approvals must survive backend restarts (DB-backed).
"""
import pytest
import json
from python.governance.approval_manager import ApprovalManager
from python.models import ApprovalRequest
from python.database import get_db_context


def _register_hold(mgr: ApprovalManager) -> str:
    return mgr.register_hold(
        task_id="TSK-TEST-001",
        plan_id="plan-test-123",
        tool_name="set_production_load",
        arguments={"asset_id": "AST-01", "load_percent": 65},
        delegation_id="delg-test-abc",
        reason="Test hold for persistence check",
    )


def test_hold_persists_to_database():
    """register_hold must create a record in DB."""
    mgr = ApprovalManager()
    action_id = _register_hold(mgr)

    with get_db_context() as db:
        record = db.query(ApprovalRequest).filter(ApprovalRequest.action_id == action_id).first()
        assert record is not None
        assert record.tool_name == "set_production_load"
        assert record.status == "PENDING_APPROVAL"
        assert record.armoriq_status == "HOLD"


def test_new_manager_instance_sees_existing_approvals():
    """A new ApprovalManager instance (simulating restart) must see existing records."""
    mgr1 = ApprovalManager()
    action_id = _register_hold(mgr1)

    # Simulate restart: create fresh instance
    mgr2 = ApprovalManager()
    approval = mgr2.get_approval(action_id)

    assert approval is not None
    assert approval["action_id"] == action_id
    assert approval["status"] == "PENDING_APPROVAL"
    assert approval["tool_name"] == "set_production_load"


def test_list_approvals_returns_pending():
    """list_approvals must return all PENDING_APPROVAL records."""
    mgr = ApprovalManager()
    action_id = _register_hold(mgr)

    items = mgr.list_approvals(status="PENDING_APPROVAL")
    ids = [i["action_id"] for i in items]
    assert action_id in ids


def test_approval_status_updated_after_rejection():
    """After rejection, status must be REJECTED in DB."""
    mgr = ApprovalManager()
    action_id = _register_hold(mgr)

    result = mgr.process_rejection(
        action_id=action_id,
        reviewer="test_reviewer@test.com",
        reason="Test rejection",
    )
    assert result["status"] == "success"

    approval = mgr.get_approval(action_id)
    assert approval["status"] == "REJECTED"
    assert approval["reviewed_by"] == "test_reviewer@test.com"
    assert approval["review_notes"] == "Test rejection"


def test_double_approval_fails():
    """Approving/rejecting an already-processed request must return error."""
    mgr = ApprovalManager()
    action_id = _register_hold(mgr)

    mgr.process_rejection(action_id=action_id, reviewer="r@r.com", reason="First rejection")
    result = mgr.process_rejection(action_id=action_id, reviewer="r@r.com", reason="Second rejection")
    assert result["status"] == "error"


def test_nonexistent_approval_returns_error():
    mgr = ApprovalManager()
    result = mgr.process_rejection("ACT-NONEXISTENT", "r@r.com", "test")
    assert result["status"] == "error"
