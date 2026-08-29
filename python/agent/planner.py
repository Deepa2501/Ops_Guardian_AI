from typing import Dict, Any, List, Tuple, Union
from python.governance.plan_manager import PlanManager, AUTHORIZED_MAINTENANCE_TOOLS


class AgentPlanner:
    """
    Translates user directives into structured intent plans
    and registers them with ArmorIQ via capture_plan().
    Works in all governance modes: sdk, mock, disabled.
    """

    def __init__(self):
        self.plan_manager = PlanManager()

    def build_and_capture_plan(
        self,
        task_prompt: str,
        asset_id: str = "AST-01",
    ) -> Tuple[Any, Any, Dict[str, Any]]:
        """
        Captures the official ArmorIQ authorization plan.
        Only maintenance, telemetry, diagnosis, and work order operations are authorized.
        Production configuration setpoints remain strictly unauthorized.
        """
        plan_capture, intent_token = self.plan_manager.create_maintenance_plan(task_prompt)

        plan_summary = {
            "plan_id": intent_token.plan_id,
            "plan_hash": intent_token.plan_hash,
            "token_id": intent_token.token_id,
            "goal": task_prompt,
            "authorized_tools": AUTHORIZED_MAINTENANCE_TOOLS,
            "unauthorized_tools": ["set_production_load", "modify_safety_interlock", "delete_asset_record"],
            "total_steps": intent_token.total_steps,
        }

        return plan_capture, intent_token, plan_summary
