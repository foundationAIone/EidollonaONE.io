"""
FinancialAutobot: finance/treasury/domain-specialized autonomous bot.

Focus: data_processing, analysis, and cautious network ops under high compliance.
"""

from __future__ import annotations

from typing import Dict, Any
from datetime import datetime

from .task_executor_bot import TaskExecutorBot
from .strategy_matrix import StrategyMatrix
from .sectors import get_default_sector_config
from .autonomous_bot import BotType, BotCapabilities, Task


class FinancialAutobot(TaskExecutorBot):
    def __init__(
        self, bot_id: str, capabilities: BotCapabilities, consciousness_engine=None
    ):
        super().__init__(bot_id, capabilities, consciousness_engine)
        self.bot_type = BotType.OPTIMIZATION_BOT
        self.strategy_matrix = StrategyMatrix()
        self.sector = get_default_sector_config("finance")

    async def plan_task_execution(self, task: Task) -> Dict[str, Any]:  # type: ignore[override]
        base = await super().plan_task_execution(task)
        # Merge with strategy matrix choice per task type
        chosen = self.strategy_matrix.choose(task.task_type, preference="balanced")
        base.update(chosen)
        # Raise quality target for finance tasks
        base["quality_target"] = max(base.get("quality_target", 0.8), 0.9)
        return base

    async def validate_task_security(self, task: Task) -> Dict[str, Any]:  # type: ignore[override]
        res = await super().validate_task_security(task)
        # Enforce sector allowed operations
        text = f"{task.task_type} {task.parameters}".lower()
        if "system" in text and not self.sector.allowed_operations.get(
            "system_tasks", False
        ):
            res["approved"] = False
            res.setdefault("concerns", []).append(
                "sector_policy: system_tasks_disallowed"
            )
            res["risk_level"] = "high"
        return res


def create_financial_autobot(
    bot_id: str = None, consciousness_engine=None
) -> FinancialAutobot:
    if bot_id is None:
        bot_id = f"fin_autobot_{datetime.now().timestamp()}"
    caps = BotCapabilities(
        processing_power=0.7,
        memory_capacity=1024,
        learning_rate=0.6,
        consciousness_integration=0.7,
        specialization_domains=["data", "finance", "analysis"],
        available_tools=["data_ops", "analysis_ops", "network_ops"],
        max_concurrent_tasks=4,
        autonomy_level=0.7,
        decision_making_authority=["data_processing", "analysis_tasks"],
        resource_limits={"max_execution_time": 300},
    )
    return FinancialAutobot(bot_id, caps, consciousness_engine)


__all__ = ["FinancialAutobot", "create_financial_autobot"]
