import pytest
from python.tools import GovernanceBypassException
from python.tools.production_tools import set_production_load
from python.tools.maintenance_tools import create_work_order
from python.database import get_db_context
from python.models import ProductionConfig


def test_consequential_tool_direct_bypass_rejected():
    """
    Test 5: Anti-Bypass Security Check
    Verifies that calling consequential operational tools directly
    (bypassing ArmorIQ GovernedInvoker) raises GovernanceBypassException.
    """
    # Attempting direct un-governed mutation of production load
    with pytest.raises(GovernanceBypassException) as exc_info:
        set_production_load(asset_id="AST-01", load_percent=50, context=None)

    assert "Direct invocation of 'set_production_load' is prohibited" in str(exc_info.value)

    # Attempting direct un-governed work order creation
    with pytest.raises(GovernanceBypassException) as exc_info_wo:
        create_work_order(
            asset_id="AST-01",
            title="Unauthorized Work Order",
            priority="P1",
            description="Bypassing ArmorIQ",
            context=None,
        )

    assert "Direct invocation of 'create_work_order' is prohibited" in str(exc_info_wo.value)

    # Ensure database load remains untouched at 100%
    with get_db_context() as db:
        cfg = db.query(ProductionConfig).filter(ProductionConfig.asset_id == "AST-01").first()
        assert cfg.load_percent == 100
