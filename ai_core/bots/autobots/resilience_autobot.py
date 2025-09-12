"""
ResilienceAutobot: operations resilience, monitoring, and recovery.
"""

from __future__ import annotations

from typing import Dict, Any
from datetime import datetime

from .task_executor_bot import TaskExecutorBot
from .strategy_matrix import StrategyMatrix
from .sectors import get_default_sector_config
from .autonomous_bot import BotType, BotCapabilities, Task


class ResilienceAutobot(TaskExecutorBot):
    def __init__(
        self, bot_id: str, capabilities: BotCapabilities, consciousness_engine=None
    ):
        super().__init__(bot_id, capabilities, consciousness_engine)
        self.bot_type = BotType.DIAGNOSTIC_BOT
        self.strategy_matrix = StrategyMatrix()
        self.sector = get_default_sector_config("resilience")

    async def plan_task_execution(self, task: Task) -> Dict[str, Any]:  # type: ignore[override]
        base = await super().plan_task_execution(task)
        chosen = self.strategy_matrix.choose(task.task_type, preference="balanced")
        base.update(chosen)
        base["quality_target"] = max(base.get("quality_target", 0.8), 0.9)
        base.setdefault("timeout", 120)
        return base

    async def validate_task_security(self, task: Task) -> Dict[str, Any]:  # type: ignore[override]
        res = await super().validate_task_security(task)
        text = f"{task.task_type} {task.parameters}".lower()
        # Extra conservative: block destructive system operations
        if any(
            kw in text for kw in ["delete", "format", "shutdown", "restart", "kill"]
        ):
            res["approved"] = False
            res.setdefault("concerns", []).append(
                "resilience_policy: destructive_ops_blocked"
            )
            res["risk_level"] = "high"
        return res


def create_resilience_autobot(
    bot_id: str = None, consciousness_engine=None
) -> ResilienceAutobot:
    if bot_id is None:
        bot_id = f"res_autobot_{datetime.now().timestamp()}"
    caps = BotCapabilities(
        processing_power=0.65,
        memory_capacity=768,
        learning_rate=0.5,
        consciousness_integration=0.7,
        specialization_domains=["monitoring", "ops", "recovery"],
        available_tools=["system_ops", "analysis_ops", "data_ops"],
        max_concurrent_tasks=3,
        autonomy_level=0.6,
        decision_making_authority=["analysis_tasks", "system_administration"],
        resource_limits={"max_execution_time": 600},
    )
    return ResilienceAutobot(bot_id, caps, consciousness_engine)


__all__ = ["ResilienceAutobot", "create_resilience_autobot"]
