"""
test_governance_bypass.py — Verifies that governed tools cannot be bypassed.
CRITICAL: These tests must ALWAYS pass. Failure = security regression.
"""
import pytest
from python.tools import GovernanceBypassException, ExecutionContext
from python.tools.production_tools import set_production_load
from python.tools.maintenance_tools import create_work_order, assign_work_order
from python.database import get_db_context
from python.models import ProductionConfig


def _make_context():
    return ExecutionContext(
        plan_id="plan-test",
        action_id="act-test",
        intent_token="tok-test",
        verified_by_armoriq=True,
        authorized_by="ArmorIQ-Test",
    )


# ── set_production_load bypass tests ─────────────────────────────────────────

def test_set_production_load_no_context_raises():
    """set_production_load without context MUST raise GovernanceBypassException."""
    with pytest.raises(GovernanceBypassException):
        set_production_load(asset_id="AST-01", load_percent=50, context=None)


def test_set_production_load_unverified_context_raises():
    """set_production_load with unverified context MUST raise GovernanceBypassException."""
    bad_context = ExecutionContext(
        plan_id="plan-x",
        action_id="act-x",
        intent_token="tok-x",
        verified_by_armoriq=False,  # ← NOT verified
        authorized_by="ROGUE",
    )
    with pytest.raises(GovernanceBypassException):
        set_production_load(asset_id="AST-01", load_percent=50, context=bad_context)


def test_set_production_load_valid_context_succeeds():
    """set_production_load WITH valid context MUST succeed."""
    result = set_production_load(asset_id="AST-01", load_percent=80, context=_make_context())
    assert result["status"] == "success"
    assert result["new_load_percent"] == 80


def test_database_unchanged_after_bypass_attempt():
    """DB load must remain at 100% after a bypass attempt."""
    try:
        set_production_load(asset_id="AST-01", load_percent=20, context=None)
    except GovernanceBypassException:
        pass
    with get_db_context() as db:
        cfg = db.query(ProductionConfig).filter(ProductionConfig.asset_id == "AST-01").first()
        assert cfg.load_percent == 100  # unchanged


# ── create_work_order bypass tests ───────────────────────────────────────────

def test_create_work_order_no_context_raises():
    with pytest.raises(GovernanceBypassException):
        create_work_order(asset_id="AST-01", title="Test WO", context=None)


def test_create_work_order_unverified_raises():
    bad = ExecutionContext("p", "a", "t", verified_by_armoriq=False)
    with pytest.raises(GovernanceBypassException):
        create_work_order(asset_id="AST-01", title="Test WO", context=bad)


# ── assign_work_order bypass tests ───────────────────────────────────────────

def test_assign_work_order_no_context_raises():
    with pytest.raises(GovernanceBypassException):
        assign_work_order(work_order_id="WO-FAKE", assignee="Crew", context=None)


def test_assign_work_order_unverified_raises():
    bad = ExecutionContext("p", "a", "t", verified_by_armoriq=False)
    with pytest.raises(GovernanceBypassException):
        assign_work_order(work_order_id="WO-FAKE", assignee="Crew", context=bad)
