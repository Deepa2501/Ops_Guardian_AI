import uuid
import datetime
from typing import Optional, Dict, Any
from python.database import get_db_context
from python.models import WorkOrder, Asset
from python.tools import ExecutionContext, GovernanceBypassException


def create_work_order(
    asset_id: str,
    title: str,
    priority: str = "P1",
    description: str = "",
    context: Optional[ExecutionContext] = None,
) -> Dict[str, Any]:
    """
    Creates a formal preventive maintenance work order in SQLite.
    Governed consequential action: requires valid ExecutionContext.
    """
    if context is None or not context.verified_by_armoriq:
        raise GovernanceBypassException(
            "CRITICAL SECURITY REJECTION: Direct invocation of 'create_work_order' is prohibited. "
            "Action must be authorized through GovernedInvoker with ArmorIQ plan token."
        )

    wo_id = f"WO-{uuid.uuid4().hex[:8].upper()}"

    with get_db_context() as db:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            return {"status": "error", "message": f"Asset {asset_id} not found"}

        work_order = WorkOrder(
            id=wo_id,
            asset_id=asset_id,
            title=title,
            description=description,
            priority=priority,
            assigned_to="UNASSIGNED",
            status="CREATED",
            plan_id=context.plan_id,
            created_at=datetime.datetime.utcnow(),
        )
        db.add(work_order)
        db.commit()

        return {
            "status": "success",
            "work_order_id": wo_id,
            "asset_id": asset_id,
            "title": title,
            "priority": priority,
            "plan_id": context.plan_id,
            "action_id": context.action_id,
            "message": f"Work order {wo_id} successfully registered in SQLite database.",
        }


def assign_work_order(
    work_order_id: str,
    assignee: str,
    context: Optional[ExecutionContext] = None,
) -> Dict[str, Any]:
    """
    Assigns an existing work order to a specialized mechanical engineering crew.
    Governed consequential action: requires valid ExecutionContext.
    """
    if context is None or not context.verified_by_armoriq:
        raise GovernanceBypassException(
            "CRITICAL SECURITY REJECTION: Direct invocation of 'assign_work_order' is prohibited. "
            "Action must be authorized through GovernedInvoker with ArmorIQ plan token."
        )

    with get_db_context() as db:
        wo = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
        if not wo:
            return {"status": "error", "message": f"Work Order {work_order_id} not found"}

        wo.assigned_to = assignee
        wo.status = "ASSIGNED"
        db.commit()

        return {
            "status": "success",
            "work_order_id": work_order_id,
            "assigned_to": assignee,
            "status_update": "ASSIGNED",
            "message": f"Work order {work_order_id} assigned to '{assignee}' in SQLite database.",
        }
