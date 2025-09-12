import asyncio
import sys
import pathlib

import pytest

# Ensure project root is on path
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_core.bots.autobots import (
    AutobotCoordinator,
    GovernanceGate,
    Task,
    TaskPriority,
    BotCapabilities,
)
from ai_core.bots.autobots import TaskExecutorBot


class DummyConsciousness:
    def get_coherence_level(self):
        return 0.75


@pytest.mark.asyncio
async def test_autobot_coordinator_plan_and_dispatch():
    gate = GovernanceGate(min_ethos_score=0.4)
    coord = AutobotCoordinator(gate)

    caps = BotCapabilities(
        processing_power=0.5,
        memory_capacity=256,
        learning_rate=0.5,
        consciousness_integration=0.6,
        specialization_domains=["data", "file"],
        available_tools=["data_ops"],
        max_concurrent_tasks=2,
        autonomy_level=0.6,
        decision_making_authority=["data_processing"],
        resource_limits={"max_execution_time": 60},
    )

    bot = TaskExecutorBot("t1", caps, DummyConsciousness())
    coord.add_bot(bot)

    t = Task(
        task_id="1",
        task_type="data_processing",
        description="helpfully analyze data",
        priority=TaskPriority.NORMAL,
        parameters={
            "operation": "compute_metrics",
            "data": [1, 2, 3],
            "metrics": "numerical",
        },
    )

    bot_id, decision = coord.plan_assignment(t)
    assert decision.approved and bot_id

    # Dispatch and give the loop a tick to queue
    coord.dispatch_task(t)

    # Start the bot explicitly in this controlled test loop
    await bot.start()

    # Give it a moment to process the queued task
    await asyncio.sleep(0.2)

    # The bot should have recorded the task as active or completed soon
    assert t.assigned_bot == bot.bot_id

    # Shutdown to cleanup background loop
    await bot.shutdown()
