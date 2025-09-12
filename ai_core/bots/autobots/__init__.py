"""
Autobots: advanced autonomous agents with governance and strategy orchestration.
"""

from .autonomous_bot import (
    AutonomousBot,
    BotType,
    BotState,
    TaskPriority,
    BotCapabilities,
    Task,
)
from .autobot_core import AutobotCoordinator, GovernanceGate, GovernanceDecision
from .strategy_matrix import Strategy, StrategyMatrix
from .task_executor_bot import TaskExecutorBot, create_task_executor_bot
from .financial_autobot import FinancialAutobot, create_financial_autobot
from .governance_autobot import GovernanceAutobot, create_governance_autobot
from .resilience_autobot import ResilienceAutobot, create_resilience_autobot
from .legal_autobot import LegalAutobot, create_legal_autobot
from .community_autobot import CommunityAutobot, create_community_autobot
from .security_autobot import SecurityAutobot, create_security_autobot
from .data_autobot import DataAutobot, create_data_autobot
from .arbitrage_autobot import ArbitrageAutobot, create_arbitrage_autobot
from .global_deployments import DeploymentRegistry, start_minimal_fleet, stop_fleet

__all__ = [
    # Base framework
    "AutonomousBot",
    "BotType",
    "BotState",
    "TaskPriority",
    "BotCapabilities",
    "Task",
    # Orchestration/Governance
    "AutobotCoordinator",
    "GovernanceGate",
    "GovernanceDecision",
    # Strategy
    "Strategy",
    "StrategyMatrix",
    # Concrete bots
    "TaskExecutorBot",
    "create_task_executor_bot",
    # Specializations
    "FinancialAutobot",
    "create_financial_autobot",
    "GovernanceAutobot",
    "create_governance_autobot",
    "ResilienceAutobot",
    "create_resilience_autobot",
    "LegalAutobot",
    "create_legal_autobot",
    "CommunityAutobot",
    "create_community_autobot",
    "SecurityAutobot",
    "create_security_autobot",
    "DataAutobot",
    "create_data_autobot",
    "ArbitrageAutobot",
    "create_arbitrage_autobot",
    # Deployments
    "DeploymentRegistry",
    "start_minimal_fleet",
    "stop_fleet",
]
