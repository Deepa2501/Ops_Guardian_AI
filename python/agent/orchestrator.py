import logging
from typing import Dict, Any, List, Optional
from python.agent.operations_agent import OperationsAgent
from python.database import get_db_context
from python.models import AgentTask

logger = logging.getLogger("opsguardian.agent.orchestrator")


class AgentOrchestrator:
    """
    Coordinates agent run lifecycles, state monitoring, and task telemetry.
    """

    def __init__(self):
        self.operations_agent = OperationsAgent()

    def run_operational_task(
        self,
        task_prompt: str = "Monitor Production Unit A, analyze reliability problems, and autonomously create preventive maintenance work orders.",
        asset_id: str = "AST-01",
    ) -> Dict[str, Any]:
        """
        Launches governed autonomous execution run.
        """
        logger.info("Starting governed agent task: '%s' on asset %s", task_prompt, asset_id)
        return self.operations_agent.run(task_prompt=task_prompt, asset_id=asset_id)

    def list_tasks(self) -> List[Dict[str, Any]]:
        with get_db_context() as db:
            tasks = db.query(AgentTask).order_by(AgentTask.created_at.desc()).all()
            return [
                {
                    "id": t.id,
                    "goal": t.goal,
                    "status": t.status,
                    "plan_id": t.plan_id,
                    "plan_hash": t.plan_hash,
                    "steps_count": t.steps_count,
                    "summary": t.summary,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in tasks
            ]


# Global Singleton
orchestrator = AgentOrchestrator()
