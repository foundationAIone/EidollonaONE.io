"""DQN Trading Agent (SE41 Integrated)

What
----
Implements a lightweight Deep Q-Network style agent for discrete trading
actions (e.g., {HOLD, BUY, SELL, FLAT}) with governance-aware reward shaping.

Why
---
1. Provides baseline value-based RL policy for comparison.
2. Risk-aware reward reduces tail exposure (penalizes high VaR / instability).
3. Deterministic seeding & simple MLP allow reproducible CI self-tests.
4. Symbolic governance hints modulate exploration vs exploitation.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional
import math
import random

try:  # pragma: no cover
    from symbolic_core.symbolic_equation41 import SymbolicEquation41, SE41Signals  # type: ignore
    from symbolic_core.se41_context import assemble_se41_context  # type: ignore
except Exception:  # pragma: no cover

    class SE41Signals:
        def __init__(self, risk=0.4, uncertainty=0.4, coherence=0.6):
            self.risk = risk
            self.uncertainty = uncertainty
            self.coherence = coherence

    class SymbolicEquation41:  # type: ignore
        def evaluate(self, ctx):
            return SE41Signals(
                ctx.get("risk_hint", 0.4),
                ctx.get("uncertainty_hint", 0.4),
                ctx.get("coherence_hint", 0.6),
            )

    def assemble_se41_context(**kw):
        return kw


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


Action = int  # 0=HOLD,1=BUY,2=SELL,3=FLAT


@dataclass
class Transition:
    state: List[float]
    action: Action
    reward: float
    next_state: List[float]
    done: bool


class TinyMLP:
    def __init__(self, input_dim: int, hidden: int, output_dim: int, seed: int = 42):
        random.seed(seed)

        def init(m, n):
            return [[random.uniform(-0.1, 0.1) for _ in range(n)] for _ in range(m)]

        self.w1 = init(hidden, input_dim)
        self.b1 = [0.0] * hidden
        self.w2 = init(output_dim, hidden)
        self.b2 = [0.0] * output_dim

    def forward(self, x: List[float]) -> List[float]:
        h = []
        for i in range(len(self.w1)):
            s = self.b1[i]
            for j, v in enumerate(x):
                s += self.w1[i][j] * v
            h.append(math.tanh(s))
        y = []
        for k in range(len(self.w2)):
            s = self.b2[k]
            for j, v in enumerate(h):
                s += self.w2[k][j] * v
            y.append(s)
        return y

    def train_step(
        self, batch: List[Tuple[List[float], List[float]]], lr: float = 1e-3
    ) -> None:
        # Simple SGD on MSE
        for x, target in batch:
            # forward
            h_raw = []
            h = []
            for i in range(len(self.w1)):
                s = self.b1[i]
                for j, v in enumerate(x):
                    s += self.w1[i][j] * v
                h_raw.append(s)
                h.append(math.tanh(s))
            y = []
            for k in range(len(self.w2)):
                s = self.b2[k]
                for j, v in enumerate(h):
                    s += self.w2[k][j] * v
                y.append(s)
            # gradients
            dy = [y[i] - target[i] for i in range(len(y))]
            for k in range(len(self.w2)):
                for j in range(len(self.w2[k])):
                    self.w2[k][j] -= lr * dy[k] * h[j]
                self.b2[k] -= lr * dy[k]
            # backprop to hidden
            dh = [0.0] * len(h)
            for j in range(len(h)):
                for k in range(len(self.w2)):
                    dh[j] += dy[k] * self.w2[k][j]
            for j in range(len(h)):
                if abs(h[j]) < 1.0:
                    dh[j] *= 1 - math.tanh(h_raw[j]) ** 2
            for i in range(len(self.w1)):
                for j in range(len(self.w1[i])):
                    self.w1[i][j] -= lr * dh[i] * x[j]
                self.b1[i] -= lr * dh[i]


class DQNAgent:
    def __init__(
        self,
        state_dim: int,
        gamma: float = 0.99,
        capacity: int = 5000,
        batch_size: int = 32,
        symbolic: Optional[SymbolicEquation41] = None,
    ) -> None:
        self.state_dim = state_dim
        self.gamma = gamma
        self.capacity = capacity
        self.batch_size = batch_size
        self.memory: List[Transition] = []
        self.model = TinyMLP(state_dim, 48, 4)
        self.symbolic = symbolic or SymbolicEquation41()
        self.epsilon = 0.2
        self.step_count = 0

    def policy(
        self, state: List[float], risk_hint: float = 0.3, uncertainty_hint: float = 0.3
    ) -> Action:
        # Adaptive exploration: more exploration at high uncertainty / risk
        adaptive_eps = self.epsilon + 0.3 * _clamp01(
            (risk_hint + uncertainty_hint) / 2.0
        )
        if random.random() < adaptive_eps:
            return random.randint(0, 3)
        q = self.model.forward(state)
        return int(max(range(len(q)), key=lambda i: q[i]))

    def remember(self, tr: Transition) -> None:
        if len(self.memory) >= self.capacity:
            self.memory.pop(0)
        self.memory.append(tr)

    def _governance_adjust_reward(self, base_reward: float, se: SE41Signals) -> float:
        penalty = 0.5 * se.risk + 0.4 * se.uncertainty
        bonus = 0.3 * se.coherence
        return base_reward - penalty + bonus

    def optimize(self) -> None:
        if len(self.memory) < self.batch_size:
            return
        batch = random.sample(self.memory, self.batch_size)
        targets: List[Tuple[List[float], List[float]]] = []
        for tr in batch:
            q_vals = self.model.forward(tr.state)
            next_q = self.model.forward(tr.next_state) if not tr.done else [0.0] * 4
            target_val = tr.reward + self.gamma * max(next_q)
            q_vals_adj = q_vals[:]
            q_vals_adj[tr.action] = target_val
            targets.append((tr.state, q_vals_adj))
        self.model.train_step(targets)

    def step(
        self,
        state: List[float],
        action: Action,
        base_reward: float,
        next_state: List[float],
        done: bool,
        risk_hint: float,
        uncertainty_hint: float,
        coherence_hint: float,
    ) -> None:
        se = self.symbolic.evaluate(
            assemble_se41_context(
                risk_hint=risk_hint,
                uncertainty_hint=uncertainty_hint,
                coherence_hint=coherence_hint,
            )
        )
        reward = self._governance_adjust_reward(base_reward, se)
        self.remember(Transition(state, action, reward, next_state, done))
        self.optimize()
        self.step_count += 1

    def snapshot(self) -> Dict[str, Any]:
        return {
            "memory": len(self.memory),
            "epsilon": self.epsilon,
            "steps": self.step_count,
        }


def _selftest() -> int:  # pragma: no cover
    random.seed(0)
    agent = DQNAgent(state_dim=6)
    s = [0.0] * 6
    for t in range(120):
        a = agent.policy(s)
        ns = [v + random.uniform(-0.05, 0.05) for v in s]
        base_r = random.uniform(-1, 1)
        agent.step(
            s,
            a,
            base_r,
            ns,
            False,
            risk_hint=0.3,
            uncertainty_hint=0.2,
            coherence_hint=0.7,
        )
        s = ns
    snap = agent.snapshot()
    assert "memory" in snap
    print("DQNAgent selftest", snap["memory"])
    return 0


__all__ = ["DQNAgent", "Transition"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    agent = DQNAgent(5)
    print(json.dumps(agent.snapshot(), indent=2))
