"""
Strategy Matrix: portfolio and selector of execution strategies for Autobots.

Why: Centralize multi-strategy definitions (speed vs. quality vs. cost),
track empirical performance, and adapt selections per task type.

What for: Provide a consistent way for bots/coordinator to request a plan,
rebalance based on results, and emit telemetry to dashboards or logs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class Strategy:
    name: str
    params: Dict[str, Any]
    weight: float = 1.0
    last_updated: datetime = field(default_factory=datetime.now)


class StrategyMatrix:
    """
    Maintains per-task-type strategies and performance scores.
    """

    def __init__(self) -> None:
        self._matrix: Dict[str, List[Strategy]] = {}
        self._scores: Dict[str, Dict[str, float]] = (
            {}
        )  # task_type -> strategy_name -> score

    def ensure_defaults(self, task_type: str) -> None:
        if task_type in self._matrix:
            return
        # Three archetypes: speed, balanced, quality
        self._matrix[task_type] = [
            Strategy(
                "speed",
                {"approach": "fast", "quality_target": 0.65, "time_limit": 60},
                1.0,
            ),
            Strategy(
                "balanced",
                {"approach": "balanced", "quality_target": 0.8, "time_limit": 180},
                1.0,
            ),
            Strategy(
                "quality",
                {"approach": "thorough", "quality_target": 0.92, "time_limit": 600},
                1.0,
            ),
        ]
        self._scores[task_type] = {s.name: 0.5 for s in self._matrix[task_type]}

    def list_strategies(self, task_type: str) -> List[Strategy]:
        self.ensure_defaults(task_type)
        return list(self._matrix[task_type])

    def choose(
        self, task_type: str, preference: Optional[str] = None
    ) -> Dict[str, Any]:
        """Return params for the best strategy, optionally biased by preference name."""
        self.ensure_defaults(task_type)
        strategies = self._matrix[task_type]
        scores = self._scores.get(task_type, {})

        # Preference boost
        def effective_score(s: Strategy) -> float:
            base = scores.get(s.name, 0.5)
            boost = 0.08 if preference and s.name == preference else 0.0
            return base * s.weight + boost

        chosen = max(strategies, key=effective_score)
        return dict(chosen.params)

    def record_outcome(
        self,
        task_type: str,
        strategy_name: str,
        success: bool,
        quality_score: float = 0.8,
        duration_s: float = 0.0,
        emit: Optional[callable] = None,
    ) -> None:
        """
        Update scores based on outcomes. Faster + higher quality increases score.
        """
        self.ensure_defaults(task_type)
        scores = self._scores[task_type]

        # Normalize inputs
        q = max(0.0, min(1.0, quality_score))
        fast_bonus = 0.05 if duration_s and duration_s < 60 else 0.0
        success_delta = 0.06 if success else -0.08
        update = success_delta + 0.15 * (q - 0.75) + fast_bonus

        scores[strategy_name] = max(
            0.0, min(1.0, scores.get(strategy_name, 0.5) + update)
        )

        if emit:
            emit(
                {
                    "ts": datetime.now().isoformat(),
                    "task_type": task_type,
                    "strategy": strategy_name,
                    "success": success,
                    "quality": q,
                    "duration_s": duration_s,
                    "new_score": scores[strategy_name],
                }
            )

    def rebalance(self, task_type: str) -> None:
        """
        Adjust weights using softmax-like normalization from scores.
        """
        self.ensure_defaults(task_type)
        strategies = self._matrix[task_type]
        scores = self._scores.get(task_type, {})

        # Convert score to weight in [0.5, 1.5]
        total = 0.0
        for s in strategies:
            score = scores.get(s.name, 0.5)
            s.weight = 0.5 + score
            total += s.weight
        if total:
            for s in strategies:
                s.weight /= total

    def set_strategies(self, task_type: str, strategies: List[Strategy]) -> None:
        self._matrix[task_type] = strategies
        self._scores[task_type] = {s.name: 0.5 for s in strategies}

    def snapshot(self) -> Dict[str, Any]:
        return {
            t: {
                "strategies": [
                    {"name": s.name, "weight": s.weight, "params": s.params}
                    for s in arr
                ],
                "scores": self._scores.get(t, {}),
            }
            for t, arr in self._matrix.items()
        }


__all__ = ["Strategy", "StrategyMatrix"]
