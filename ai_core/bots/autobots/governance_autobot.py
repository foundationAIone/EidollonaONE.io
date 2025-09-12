"""
GovernanceAutobot: governance/legal policy assistant with strict approvals.
"""

from __future__ import annotations

from typing import Dict, Any
from datetime import datetime

from .task_executor_bot import TaskExecutorBot
from .strategy_matrix import StrategyMatrix
from .sectors import get_default_sector_config
from .autonomous_bot import BotType, BotCapabilities, Task


class GovernanceAutobot(TaskExecutorBot):
    def __init__(
        self, bot_id: str, capabilities: BotCapabilities, consciousness_engine=None
    ):
        super().__init__(bot_id, capabilities, consciousness_engine)
        self.bot_type = BotType.DIAGNOSTIC_BOT
        self.strategy_matrix = StrategyMatrix()
        self.sector = get_default_sector_config("governance")

    async def plan_task_execution(self, task: Task) -> Dict[str, Any]:  # type: ignore[override]
        base = await super().plan_task_execution(task)
        chosen = self.strategy_matrix.choose(task.task_type, preference="quality")
        base.update(chosen)
        base["quality_target"] = max(base.get("quality_target", 0.85), 0.95)
        return base

    async def validate_task_security(self, task: Task) -> Dict[str, Any]:  # type: ignore[override]
        res = await super().validate_task_security(task)
        # Governance requires human_review hint for sensitive ops
        if self.sector.policy_hints.get("human_review"):
            text = f"{task.task_type} {task.parameters}".lower()
            if any(k in text for k in ["delete", "shutdown", "privileged", "admin"]):
                res["approved"] = False
                res.setdefault("concerns", []).append("human_review_required")
                res["risk_level"] = "high"
        return res


def create_governance_autobot(
    bot_id: str = None, consciousness_engine=None
) -> GovernanceAutobot:
    if bot_id is None:
        bot_id = f"gov_autobot_{datetime.now().timestamp()}"
    caps = BotCapabilities(
        processing_power=0.6,
        memory_capacity=512,
        learning_rate=0.5,
        consciousness_integration=0.75,
        specialization_domains=["policy", "legal", "governance"],
        available_tools=["analysis_ops", "data_ops"],
        max_concurrent_tasks=2,
        autonomy_level=0.5,
        decision_making_authority=["analysis_tasks"],
        resource_limits={"max_execution_time": 300},
    )
    return GovernanceAutobot(bot_id, caps, consciousness_engine)


__all__ = ["GovernanceAutobot", "create_governance_autobot"]
