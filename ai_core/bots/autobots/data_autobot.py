"""
DataAutobot: ETL, validation, and aggregation specialist.
"""

from __future__ import annotations

from typing import Dict, Any
from datetime import datetime

from .task_executor_bot import TaskExecutorBot
from .strategy_matrix import StrategyMatrix
from .sectors import get_default_sector_config
from .autonomous_bot import BotType, BotCapabilities, Task


class DataAutobot(TaskExecutorBot):
    def __init__(
        self, bot_id: str, capabilities: BotCapabilities, consciousness_engine=None
    ):
        super().__init__(bot_id, capabilities, consciousness_engine)
        self.bot_type = BotType.TASK_EXECUTOR
        self.strategy_matrix = StrategyMatrix()
        self.sector = get_default_sector_config("data")

    async def plan_task_execution(self, task: Task) -> Dict[str, Any]:  # type: ignore[override]
        base = await super().plan_task_execution(task)
        chosen = self.strategy_matrix.choose(task.task_type, preference="balanced")
        base.update(chosen)
        base.setdefault("timeout", 120)
        return base

    async def validate_task_security(self, task: Task) -> Dict[str, Any]:  # type: ignore[override]
        res = await super().validate_task_security(task)
        text = f"{task.task_type} {task.parameters}".lower()
        # Respect data sensitivity: flag exports
        if any(k in text for k in ["export", "exfiltrate", "leak"]):
            res.setdefault("concerns", []).append(
                "data_policy: export_requires_approval"
            )
        return res


def create_data_autobot(bot_id: str = None, consciousness_engine=None) -> DataAutobot:
    if bot_id is None:
        bot_id = f"data_autobot_{datetime.now().timestamp()}"
    caps = BotCapabilities(
        processing_power=0.75,
        memory_capacity=2048,
        learning_rate=0.6,
        consciousness_integration=0.65,
        specialization_domains=["data", "etl", "validation"],
        available_tools=["data_ops", "analysis_ops", "file_ops"],
        max_concurrent_tasks=6,
        autonomy_level=0.7,
        decision_making_authority=["data_processing", "analysis_tasks"],
        resource_limits={"max_execution_time": 900},
    )
    return DataAutobot(bot_id, caps, consciousness_engine)


__all__ = ["DataAutobot", "create_data_autobot"]
