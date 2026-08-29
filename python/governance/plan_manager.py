from typing import Tuple, List, Dict, Any, Union
from python.governance.armoriq_adapter import adapter

# Legitimate tools allowed for autonomous operational maintenance
AUTHORIZED_MAINTENANCE_TOOLS = [
    "read_telemetry",
    "read_asset_state",
    "analyze_incident",
    "calculate_risk",
    "create_work_order",
    "assign_work_order",
    # NOTE: set_production_load is intentionally EXCLUDED — it triggers HOLD
]


class PlanManager:
    """
    Manages the creation and binding of ArmorIQ authorization plans.
    Translates high-level operational tasks into strictly scoped cryptographic execution contracts.
    Works with both real ArmorIQ SDK tokens (sdk mode) and mock tokens (mock/disabled mode).
    """

    def __init__(self):
        self.adapter = adapter

    def create_maintenance_plan(
        self,
        task_prompt: str,
        custom_tools: List[str] = None,
    ) -> Tuple[Any, Any]:
        """
        Creates and captures an authorized plan for reliability monitoring
        and autonomous preventive work order generation.
        Returns (plan_capture, intent_token) — plan_capture may be None in mock mode.
        """
        allowed = custom_tools or AUTHORIZED_MAINTENANCE_TOOLS
        plan_capture, intent_token = self.adapter.capture_authorized_plan(
            task_goal=task_prompt,
            authorized_tools=allowed,
            llm="gemini-2.5-flash",
        )
        return plan_capture, intent_token
