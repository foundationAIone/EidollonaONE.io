"""
LegalAutobot: legal/compliance documentation and review assistant.
"""

from __future__ import annotations

from typing import Dict, Any
from datetime import datetime

from .task_executor_bot import TaskExecutorBot
from .strategy_matrix import StrategyMatrix
from .sectors import get_default_sector_config
from .autonomous_bot import BotType, BotCapabilities, Task


class LegalAutobot(TaskExecutorBot):
    def __init__(
        self, bot_id: str, capabilities: BotCapabilities, consciousness_engine=None
    ):
        super().__init__(bot_id, capabilities, consciousness_engine)
        self.bot_type = BotType.DIAGNOSTIC_BOT
        self.strategy_matrix = StrategyMatrix()
        self.sector = get_default_sector_config("legal")

    async def plan_task_execution(self, task: Task) -> Dict[str, Any]:  # type: ignore[override]
        base = await super().plan_task_execution(task)
        chosen = self.strategy_matrix.choose(task.task_type, preference="quality")
        base.update(chosen)
        base["quality_target"] = max(base.get("quality_target", 0.9), 0.97)
        base.setdefault("audit", True)
        return base

    async def validate_task_security(self, task: Task) -> Dict[str, Any]:  # type: ignore[override]
        res = await super().validate_task_security(task)
        text = f"{task.task_type} {task.parameters}".lower()
        # Legal forbids system-level changes and limits network writes
        if "system" in text:
            res["approved"] = False
            res.setdefault("concerns", []).append(
                "legal_policy: system_tasks_disallowed"
            )
            res["risk_level"] = "high"
        if "upload" in text or "post" in text:
            res.setdefault("concerns", []).append(
                "legal_policy: outbound_publication_requires_review"
            )
        return res


def create_legal_autobot(bot_id: str = None, consciousness_engine=None) -> LegalAutobot:
    if bot_id is None:
        bot_id = f"legal_autobot_{datetime.now().timestamp()}"
    caps = BotCapabilities(
        processing_power=0.6,
        memory_capacity=1024,
        learning_rate=0.4,
        consciousness_integration=0.75,
        specialization_domains=["legal", "compliance", "policy"],
        available_tools=["analysis_ops", "data_ops", "file_ops"],
        max_concurrent_tasks=2,
        autonomy_level=0.5,
        decision_making_authority=["analysis_tasks"],
        resource_limits={"max_execution_time": 600},
    )
    return LegalAutobot(bot_id, caps, consciousness_engine)


__all__ = ["LegalAutobot", "create_legal_autobot"]
