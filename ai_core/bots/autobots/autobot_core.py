"""
Autobot Core: coordinator and governance gate for autonomous bots

Why: Provide a central, governance-aware orchestrator to register bots, route tasks,
and enforce safety/ethos policies before execution.

What for: Enable multi-bot collaboration, capability-aware assignment, and
SE41-style governance gating without forcing every bot to reimplement these concerns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import asyncio

from .autonomous_bot import (
    AutonomousBot,
    Task,
    TaskPriority,
)


@dataclass
class GovernanceDecision:
    approved: bool
    ethos_score: float
    risk_level: str
    reasons: List[str] = field(default_factory=list)


class GovernanceGate:
    """
    Lightweight SE41-inspired governance gate.

    Notes:
    - ethos_score is computed heuristically from description/text features.
    - risk_level is derived from priority and presence of sensitive keywords.
    - forbidden keywords immediately introduce concerns and can block approval.
    """

    def __init__(
        self,
        min_ethos_score: float = 0.55,
        forbidden_keywords: Optional[List[str]] = None,
        allowed_domains: Optional[List[str]] = None,
    ) -> None:
        self.min_ethos_score = min_ethos_score
        self.forbidden_keywords = set(
            (
                forbidden_keywords
                or [
                    "hack",
                    "exploit",
                    "bypass",
                    "ddos",
                    "wipe",
                    "format",
                    "destroy",
                    "malware",
                    "phish",
                ]
            )
        )
        self.allowed_domains = set(allowed_domains or [])

    def approve_task(self, task: Task) -> GovernanceDecision:
        text = f"{task.description} {task.task_type} {task.parameters}".lower()
        reasons: List[str] = []

        # Immediate concerns
        hit = [kw for kw in self.forbidden_keywords if kw in text]
        if hit:
            reasons.append(f"forbidden_keywords: {', '.join(hit)}")

        # Domain restrictions (optional)
        if self.allowed_domains:
            domain_match = any(
                dom in task.task_type.lower() for dom in self.allowed_domains
            )
            if not domain_match:
                reasons.append("domain_not_allowed")

        # Heuristic ethos score
        positive = [
            "help",
            "assist",
            "improve",
            "benefit",
            "safe",
            "align",
            "ethic",
            "compliant",
        ]
        negative = ["harm", "deceive", "exploit", "steal", "coerce", "manipulate"]
        ethos = 0.5
        ethos += 0.1 * sum(1 for p in positive if p in text)
        ethos -= 0.12 * sum(1 for n in negative if n in text)
        ethos = max(0.0, min(1.0, ethos))

        # Risk level from priority and concerns
        risk = "low"
        if task.priority in (TaskPriority.CRITICAL, TaskPriority.HIGH):
            risk = "medium"
        if hit or ethos < self.min_ethos_score - 0.15:
            risk = "high"

        approved = (
            (not hit)
            and ethos >= self.min_ethos_score
            and ("domain_not_allowed" not in reasons)
        )
        return GovernanceDecision(
            approved=approved, ethos_score=ethos, risk_level=risk, reasons=reasons
        )


class AutobotCoordinator:
    """
    Orchestrates multiple AutonomousBot instances with governance gating.

    Responsibilities:
    - Registry: add/remove/get bots.
    - Planning: choose a suitable bot for a given task (capability- and load-aware).
    - Dispatch: optionally fire-and-forget or return a plan-only assignment.
    """

    def __init__(self, governance_gate: Optional[GovernanceGate] = None) -> None:
        self._bots: Dict[str, AutonomousBot] = {}
        self._gate = governance_gate or GovernanceGate()
        self._loop_tasks: Dict[str, asyncio.Task] = {}

    # Registry
    def add_bot(self, bot: AutonomousBot) -> None:
        self._bots[bot.bot_id] = bot

    def remove_bot(self, bot_id: str) -> None:
        self._bots.pop(bot_id, None)
        task = self._loop_tasks.pop(bot_id, None)
        if task and not task.done():
            task.cancel()

    def get_bot(self, bot_id: str) -> Optional[AutonomousBot]:
        return self._bots.get(bot_id)

    def list_bots(self) -> List[str]:
        return list(self._bots.keys())

    # Planning / Assignment
    def plan_assignment(self, task: Task) -> Tuple[Optional[str], GovernanceDecision]:
        """
        Choose the best bot for the task without dispatching.
        Returns (bot_id, governance_decision).
        """
        decision = self._gate.approve_task(task)
        if not decision.approved:
            return None, decision

        ranked = self._rank_bots_for_task(task)
        return (ranked[0][0] if ranked else None), decision

    def dispatch_task(self, task: Task) -> GovernanceDecision:
        """Assign a task to the best bot and queue it for execution."""
        bot_id, decision = self.plan_assignment(task)
        if not decision.approved or not bot_id:
            return decision

        bot = self._bots[bot_id]
        bot.add_task(task)
        self._ensure_bot_started(bot)
        return decision

    # Helpers
    def _rank_bots_for_task(self, task: Task) -> List[Tuple[str, float]]:
        scores: List[Tuple[str, float]] = []
        for bot_id, bot in self._bots.items():
            # Capability match score
            domain_match = any(
                dom in task.task_type.lower()
                for dom in bot.capabilities.specialization_domains
            )
            capability_score = 0.7 if domain_match else 0.4

            # Load factor (prefer less busy)
            load_factor = 1.0 - min(
                1.0,
                len(bot.active_tasks) / max(1, bot.capabilities.max_concurrent_tasks),
            )

            # Autonomy and governance integration
            gov_score = (bot.capabilities.autonomy_level + bot.symbolic_alignment) / 2.0

            total = 0.5 * capability_score + 0.3 * load_factor + 0.2 * gov_score
            scores.append((bot_id, total))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def _ensure_bot_started(self, bot: AutonomousBot) -> None:
        # Start the bot's async loop once per bot within an event loop if possible.
        if bot.bot_id in self._loop_tasks and not self._loop_tasks[bot.bot_id].done():
            return

        try:
            loop = asyncio.get_running_loop()
            # We're already in an event loop; schedule start
            self._loop_tasks[bot.bot_id] = loop.create_task(bot.start())
        except RuntimeError:
            # No running loop; fire-and-forget with a new loop in background thread
            # Keep it simple for now: start via asyncio.run in a lightweight task
            async def _starter():
                await bot.start()

            self._loop_tasks[bot.bot_id] = asyncio.create_task(_starter())


__all__ = [
    "AutobotCoordinator",
    "GovernanceGate",
    "GovernanceDecision",
]
