"""
CommunityAutobot: community engagement, communications, and insights.
"""

from __future__ import annotations

from typing import Dict, Any
from datetime import datetime

from .task_executor_bot import TaskExecutorBot
from .strategy_matrix import StrategyMatrix
from .sectors import get_default_sector_config
from .autonomous_bot import BotType, BotCapabilities, Task


class CommunityAutobot(TaskExecutorBot):
    def __init__(
        self, bot_id: str, capabilities: BotCapabilities, consciousness_engine=None
    ):
        super().__init__(bot_id, capabilities, consciousness_engine)
        self.bot_type = BotType.TASK_EXECUTOR
        self.strategy_matrix = StrategyMatrix()
        self.sector = get_default_sector_config("community")

    async def plan_task_execution(self, task: Task) -> Dict[str, Any]:  # type: ignore[override]
        base = await super().plan_task_execution(task)
        chosen = self.strategy_matrix.choose(task.task_type, preference="balanced")
        base.update(chosen)
        base.setdefault("timeout", 90)
        return base

    async def validate_task_security(self, task: Task) -> Dict[str, Any]:  # type: ignore[override]
        res = await super().validate_task_security(task)
        text = f"{task.task_type} {task.parameters}".lower()
        # Community bot should avoid posting without review
        if any(k in text for k in ["post", "tweet", "publish"]):
            res.setdefault("concerns", []).append(
                "community_policy: human_review_recommended"
            )
        return res


def create_community_autobot(
    bot_id: str = None, consciousness_engine=None
) -> CommunityAutobot:
    if bot_id is None:
        bot_id = f"community_autobot_{datetime.now().timestamp()}"
    caps = BotCapabilities(
        processing_power=0.55,
        memory_capacity=512,
        learning_rate=0.6,
        consciousness_integration=0.65,
        specialization_domains=["communications", "community", "analysis"],
        available_tools=["analysis_ops", "data_ops", "network_ops"],
        max_concurrent_tasks=5,
        autonomy_level=0.6,
        decision_making_authority=["analysis_tasks", "data_processing"],
        resource_limits={"max_execution_time": 300},
    )
    return CommunityAutobot(bot_id, caps, consciousness_engine)


__all__ = ["CommunityAutobot", "create_community_autobot"]
