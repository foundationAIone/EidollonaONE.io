"""
SecurityAutobot: security analysis, monitoring, and hardening assistant.
"""

from __future__ import annotations

from typing import Dict, Any
from datetime import datetime

from .task_executor_bot import TaskExecutorBot
from .strategy_matrix import StrategyMatrix
from .sectors import get_default_sector_config
from .autonomous_bot import BotType, BotCapabilities, Task


class SecurityAutobot(TaskExecutorBot):
    def __init__(
        self, bot_id: str, capabilities: BotCapabilities, consciousness_engine=None
    ):
        super().__init__(bot_id, capabilities, consciousness_engine)
        self.bot_type = BotType.DIAGNOSTIC_BOT
        self.strategy_matrix = StrategyMatrix()
        self.sector = get_default_sector_config("security")

    async def plan_task_execution(self, task: Task) -> Dict[str, Any]:  # type: ignore[override]
        base = await super().plan_task_execution(task)
        chosen = self.strategy_matrix.choose(task.task_type, preference="quality")
        base.update(chosen)
        base.setdefault("timeout", 60)
        return base

    async def validate_task_security(self, task: Task) -> Dict[str, Any]:  # type: ignore[override]
        res = await super().validate_task_security(task)
        text = f"{task.task_type} {task.parameters}".lower()
        # No intrusive actions; focus on scanning/analysis
        if any(k in text for k in ["exploit", "bypass", "attack", "penetration"]):
            res["approved"] = False
            res.setdefault("concerns", []).append(
                "security_policy: intrusive_ops_disallowed"
            )
            res["risk_level"] = "high"
        return res


def create_security_autobot(
    bot_id: str = None, consciousness_engine=None
) -> SecurityAutobot:
    if bot_id is None:
        bot_id = f"sec_autobot_{datetime.now().timestamp()}"
    caps = BotCapabilities(
        processing_power=0.7,
        memory_capacity=1024,
        learning_rate=0.55,
        consciousness_integration=0.7,
        specialization_domains=["security", "monitoring", "hardening"],
        available_tools=["analysis_ops", "system_ops", "data_ops"],
        max_concurrent_tasks=3,
        autonomy_level=0.55,
        decision_making_authority=["analysis_tasks"],
        resource_limits={"max_execution_time": 300},
    )
    return SecurityAutobot(bot_id, caps, consciousness_engine)


__all__ = ["SecurityAutobot", "create_security_autobot"]
