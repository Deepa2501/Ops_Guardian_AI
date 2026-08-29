from dataclasses import dataclass
from typing import Optional, Dict, Any


class GovernanceBypassException(PermissionError):
    """Raised when consequential tools are invoked directly bypassing the ArmorIQ governed invoker."""
    pass


@dataclass
class ExecutionContext:
    """Security execution context passed ONLY by the Python GovernedInvoker after ArmorIQ authorization."""
    plan_id: str
    action_id: str
    intent_token: str
    verified_by_armoriq: bool
    delegation_id: Optional[str] = None
    authorized_by: str = "ArmorIQ"
