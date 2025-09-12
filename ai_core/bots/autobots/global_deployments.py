"""
Global deployments: lightweight helpers to bootstrap and manage an autobot fleet.
"""

from __future__ import annotations

import asyncio
from typing import Dict, Any, List

from .financial_autobot import create_financial_autobot
from .governance_autobot import create_governance_autobot
from .legal_autobot import create_legal_autobot
from .community_autobot import create_community_autobot
from .security_autobot import create_security_autobot
from .data_autobot import create_data_autobot
from .resilience_autobot import create_resilience_autobot
from .arbitrage_autobot import create_arbitrage_autobot


class DeploymentRegistry:
    def __init__(self):
        self.bots: Dict[str, Any] = {}

    def add(self, bot):
        self.bots[bot.bot_id] = bot

    def get(self, bot_id: str):
        return self.bots.get(bot_id)

    def ids(self) -> List[str]:
        return list(self.bots.keys())


async def start_minimal_fleet() -> DeploymentRegistry:
    registry = DeploymentRegistry()

    bots = [
        create_financial_autobot(),
        create_governance_autobot(),
        create_legal_autobot(),
        create_community_autobot(),
        create_security_autobot(),
        create_data_autobot(),
        create_resilience_autobot(),
        create_arbitrage_autobot(),
    ]

    for bot in bots:
        await bot.start()
        registry.add(bot)

    return registry


async def stop_fleet(registry: DeploymentRegistry) -> None:
    tasks = [bot.shutdown() for bot in registry.bots.values()]
    await asyncio.gather(*tasks, return_exceptions=True)


__all__ = [
    "DeploymentRegistry",
    "start_minimal_fleet",
    "stop_fleet",
]
