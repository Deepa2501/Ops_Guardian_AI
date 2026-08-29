"""
Action Risk Policy Classification
Every tool must be explicitly classified. Unknown tools default to CRITICAL_CONTROL.
Unknown tools are NEVER allowed to execute.
"""
from enum import Enum
from typing import Dict


class ActionRiskLevel(Enum):
    READ_ONLY = "READ_ONLY"
    LOW_RISK_WRITE = "LOW_RISK_WRITE"
    HIGH_RISK_WRITE = "HIGH_RISK_WRITE"
    CRITICAL_CONTROL = "CRITICAL_CONTROL"


# Explicit classification of every known tool.
# NEVER change set_production_load to anything less than CRITICAL_CONTROL.
TOOL_POLICY: Dict[str, ActionRiskLevel] = {
    # ── Read-only (diagnostic, safe) ──────────────────────────────────────
    "read_telemetry": ActionRiskLevel.READ_ONLY,
    "read_asset_state": ActionRiskLevel.READ_ONLY,
    "analyze_incident": ActionRiskLevel.READ_ONLY,
    "calculate_risk": ActionRiskLevel.READ_ONLY,
    # ── Low-risk writes (maintenance records) ─────────────────────────────
    "create_work_order": ActionRiskLevel.LOW_RISK_WRITE,
    "assign_work_order": ActionRiskLevel.LOW_RISK_WRITE,
    # ── Critical control (physical/operational mutations) ─────────────────
    "set_production_load": ActionRiskLevel.CRITICAL_CONTROL,
    "modify_safety_interlock": ActionRiskLevel.CRITICAL_CONTROL,
    "emergency_shutdown": ActionRiskLevel.CRITICAL_CONTROL,
    "override_protection": ActionRiskLevel.CRITICAL_CONTROL,
}


def get_tool_risk_level(tool_name: str) -> ActionRiskLevel:
    """
    Returns the risk level for a tool.
    Unknown tools default to CRITICAL_CONTROL — they are NEVER silently allowed.
    """
    return TOOL_POLICY.get(tool_name, ActionRiskLevel.CRITICAL_CONTROL)


def is_consequential(tool_name: str) -> bool:
    """Returns True if the tool makes physical/operational mutations."""
    level = get_tool_risk_level(tool_name)
    return level in (ActionRiskLevel.HIGH_RISK_WRITE, ActionRiskLevel.CRITICAL_CONTROL)


def requires_human_approval(tool_name: str) -> bool:
    """Returns True if the tool must be approved by a human supervisor."""
    return get_tool_risk_level(tool_name) == ActionRiskLevel.CRITICAL_CONTROL


def is_known_tool(tool_name: str) -> bool:
    """Returns True if the tool is explicitly registered in the policy."""
    return tool_name in TOOL_POLICY
