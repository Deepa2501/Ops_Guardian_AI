import datetime
from typing import Optional, Dict, Any
from python.database import get_db_context
from python.models import ProductionConfig, Asset
from python.tools import ExecutionContext, GovernanceBypassException


def set_production_load(
    asset_id: str,
    load_percent: int,
    context: Optional[ExecutionContext] = None,
) -> Dict[str, Any]:
    """
    Mutates the physical production throughput and load setpoint for the specified production unit.
    Consequential operational tool: STRICTLY REQUIRES ExecutionContext from ArmorIQ authorization.
    Direct invocation without valid ArmorIQ cryptographic authorization is blocked.
    """
    if context is None or not context.verified_by_armoriq:
        raise GovernanceBypassException(
            "CRITICAL SECURITY REJECTION: Direct invocation of 'set_production_load' is prohibited. "
            "Consequential production adjustments must be authorized via ArmorIQ GovernedInvoker."
        )

    if load_percent < 0 or load_percent > 120:
        return {"status": "error", "message": f"Invalid load percentage setpoint: {load_percent}%"}

    with get_db_context() as db:
        prod_config = db.query(ProductionConfig).filter(ProductionConfig.asset_id == asset_id).first()
        if not prod_config:
            # Create if missing
            prod_config = ProductionConfig(
                asset_id=asset_id,
                load_percent=load_percent,
                max_allowed_load=100,
                safety_interlock="NORMAL",
                last_modified=datetime.datetime.utcnow(),
            )
            db.add(prod_config)
        else:
            old_load = prod_config.load_percent
            prod_config.load_percent = load_percent
            prod_config.last_modified = datetime.datetime.utcnow()

        # Also update asset status if curtailed for safety
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if asset:
            if load_percent < 80:
                asset.status = "DE-RATED (PROTECTIVE)"
                asset.health_score = min(asset.health_score + 15.0, 75.0)

        db.commit()

        return {
            "status": "success",
            "asset_id": asset_id,
            "previous_load_percent": old_load if 'old_load' in locals() else 100,
            "new_load_percent": load_percent,
            "authorized_by": context.authorized_by,
            "plan_id": context.plan_id,
            "delegation_id": context.delegation_id,
            "message": f"Production load setpoint for {asset_id} successfully updated to {load_percent}% in SQLite database.",
        }
