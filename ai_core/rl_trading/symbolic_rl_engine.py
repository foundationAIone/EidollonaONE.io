"""Symbolic RL Orchestrator (SE41)

What
----
Coordinates multiple RL agents (DQN, PPO, A3C) & integrates governance metrics
to produce ensemble action recommendation with stability weighting.

Why
---
1. Model diversification reduces overfitting risk.
2. Governance-driven reweighting lowers influence of unstable agents.
3. Provides single cohesive interface for strategy consumers.
4. Deterministic snapshot for CI.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional

from .dqn_agent import DQNAgent
from .ppo_agent import PPOAgent
from .a3c_agent import A3CAgent

from symbolic_core.symbolic_equation41 import SymbolicEquation41  # type: ignore
from symbolic_core.symbolic_equation41 import SE41Signals  # type: ignore

try:  # pragma: no cover
    from symbolic_core.context_builder import assemble_se41_context  # type: ignore
except Exception:  # pragma: no cover

    def assemble_se41_context(**kw):
        return kw


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


class SymbolicRLEngine:
    def __init__(
    self, state_dim: int, symbolic: Optional[Any] = None
    ) -> None:
        self.dqn = DQNAgent(state_dim, symbolic=symbolic)
        self.ppo = PPOAgent(state_dim, symbolic=symbolic)
        self.a3c = A3CAgent(state_dim, symbolic=symbolic)
        self.symbolic = symbolic or SymbolicEquation41()
        self.action_space = 4

    def act(
        self,
        state: List[float],
        risk_hint: float,
        uncertainty_hint: float,
        coherence_hint: float,
    ) -> int:
        # Collect actions
        a_dqn = self.dqn.policy(state, risk_hint, uncertainty_hint)
        a_ppo = self.ppo.act(state, risk_hint, uncertainty_hint, coherence_hint)
        a_a3c = self.a3c.act(state)
        # Weighting via governance (higher risk+uncertainty lowers weight)
        se: SE41Signals = self.symbolic.evaluate(
            assemble_se41_context(
                risk_hint=risk_hint,
                uncertainty_hint=uncertainty_hint,
                coherence_hint=coherence_hint,
            )
        )
        penalty = _clamp01((se.risk + se.uncertainty) / 2.0)
        w_base = 1.0 - 0.5 * penalty
        weights = {
            "dqn": w_base,
            "ppo": w_base * (1 + 0.1 * se.coherence),
            "a3c": w_base * 0.9,
        }
        votes = {
            a_dqn: weights["dqn"],
            a_ppo: weights["ppo"] + weights["dqn"] * 0.0,
            a_a3c: weights["a3c"],
        }
        # Choose action with highest cumulative vote
        best_action = max(votes.items(), key=lambda kv: kv[1])[0]
        return int(best_action)

    def step_all(
        self,
        state: List[float],
        action: int,
        reward: float,
        next_state: List[float],
        done: bool,
        risk_hint: float,
        uncertainty_hint: float,
        coherence_hint: float,
    ):
        self.dqn.step(
            state,
            action,
            reward,
            next_state,
            done,
            risk_hint,
            uncertainty_hint,
            coherence_hint,
        )
        self.ppo.step(
            state, action, reward, done, risk_hint, uncertainty_hint, coherence_hint
        )
        self.a3c.step(
            state, action, reward, done, risk_hint, uncertainty_hint, coherence_hint
        )
        if done:
            self.ppo.update()
            # finalize PPO epoch
        # a3c update occurs inside its step when done

    def snapshot(self) -> Dict[str, Any]:
        return {
            "dqn": self.dqn.snapshot(),
            "ppo": self.ppo.snapshot(),
            "a3c": self.a3c.snapshot(),
        }


def _selftest() -> int:  # pragma: no cover
    import random

    eng = SymbolicRLEngine(state_dim=6)
    s = [0.0] * 6
    for t in range(100):
        a = eng.act(s, 0.3, 0.2, 0.7)
        ns = [v + random.uniform(-0.03, 0.03) for v in s]
        r = random.uniform(-1, 1)
        eng.step_all(s, a, r, ns, False, 0.3, 0.2, 0.7)
        s = ns
    eng.step_all(s, 0, 0.1, s, True, 0.3, 0.2, 0.7)
    snap = eng.snapshot()
    assert "dqn" in snap
    print("SymbolicRLEngine selftest", snap["dqn"]["memory"])
    return 0


__all__ = ["SymbolicRLEngine"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    eng = SymbolicRLEngine(5)
    print(json.dumps(eng.snapshot(), indent=2))
