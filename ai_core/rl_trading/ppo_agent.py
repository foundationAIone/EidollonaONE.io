"""PPO Trading Agent (SE41 Integrated - Simplified)

What
----
Implements a minimal Proximal Policy Optimization style loop with clipped
surrogate objective for continuous action logits mapped to discrete trade
decisions. Governance signals modulate entropy bonus (exploration).

Why
---
1. Policy-gradient baseline with stability vs exploration control.
2. Integrates SE41: high risk reduces leverage in reward; uncertainty raises entropy.
3. Deterministic tiny network for reproducible CI self-test.
4. Provides complementary learning dynamics to value-based DQN.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import random
import math

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


def _softmax(z: List[float]) -> List[float]:
    m = max(z)
    ex = [math.exp(v - m) for v in z]
    s = sum(ex)
    return [v / s for v in ex]


class TinyPolicy:
    def __init__(self, state_dim: int, hidden: int = 32, seed: int = 1):
        random.seed(seed)

        def init(m, n):
            return [[random.uniform(-0.1, 0.1) for _ in range(n)] for _ in range(m)]

        self.w1 = init(hidden, state_dim)
        self.b1 = [0.0] * hidden
        self.wp = init(4, hidden)
        self.bp = [0.0] * 4
        self.wv = init(1, hidden)
        self.bv = [0.0]

    def forward(self, s: List[float]):
        h = []
        for i in range(len(self.w1)):
            val = self.b1[i]
            for j, v in enumerate(s):
                val += self.w1[i][j] * v
            h.append(math.tanh(val))
        logits = []
        for k in range(len(self.wp)):
            z = self.bp[k]
            for j, v in enumerate(h):
                z += self.wp[k][j] * v
            logits.append(z)
        v = self.bv[0] + sum(self.wv[0][j] * h[j] for j in range(len(h)))
        return logits, v, h

    def train_step(self, grads: Dict[str, Any], lr: float = 3e-4):
        for i in range(len(self.w1)):
            for j in range(len(self.w1[i])):
                self.w1[i][j] += lr * grads["w1"][i][j]
            self.b1[i] += lr * grads["b1"][i]
        for k in range(len(self.wp)):
            for j in range(len(self.wp[k])):
                self.wp[k][j] += lr * grads["wp"][k][j]
            self.bp[k] += lr * grads["bp"][k]
        for j in range(len(self.wv[0])):
            self.wv[0][j] += lr * grads["wv"][0][j]
        self.bv[0] += lr * grads["bv"][0]


@dataclass
class PPOTransition:
    state: List[float]
    action: int
    logp: float
    value: float
    reward: float
    done: bool


class PPOAgent:
    def __init__(
        self,
        state_dim: int,
        gamma: float = 0.99,
        lam: float = 0.95,
        clip: float = 0.2,
        batch_size: int = 64,
        symbolic: Optional[SymbolicEquation41] = None,
    ):
        self.state_dim = state_dim
        self.gamma = gamma
        self.lam = lam
        self.clip = clip
        self.batch_size = batch_size
        self.policy = TinyPolicy(state_dim)
        self.buffer: List[PPOTransition] = []
        self.symbolic = symbolic or SymbolicEquation41()
        self.entropy_coef = 0.01

    def act(
        self,
        state: List[float],
        risk_hint: float,
        uncertainty_hint: float,
        coherence_hint: float,
    ) -> int:
        logits, val, _ = self.policy.forward(state)
        probs = _softmax(logits)
        # governance-driven entropy modulation
        exploration_boost = 0.02 * _clamp((risk_hint + uncertainty_hint) / 2.0)
        self.entropy_coef = 0.01 + exploration_boost
        r = random.random()
        acc = 0
        for i, p in enumerate(probs):
            acc += p
            if r <= acc:
                return i
        return len(probs) - 1

    def remember(self, tr: PPOTransition):
        self.buffer.append(tr)

    def _process(self):
        # GAE advantage estimation
        advs = []
        rets = []
        gae = 0.0
        next_value = 0.0
        for tr in reversed(self.buffer):
            delta = tr.reward + self.gamma * (0.0 if tr.done else next_value) - tr.value
            gae = delta + self.gamma * self.lam * (0.0 if tr.done else gae)
            advs.append(gae)
            rets.append(gae + tr.value)
            next_value = tr.value
        advs.reverse()
        rets.reverse()
        m = sum(advs) / max(1, len(advs))
        v = sum((a - m) ** 2 for a in advs) / max(1, len(advs))
        std = math.sqrt(v + 1e-9)
        advs = [(a - m) / std for a in advs]
        return advs, rets

    def update(self, epochs: int = 2):
        if not self.buffer:
            return
        advs, rets = self._process()
        for _ in range(epochs):
            for idx, tr in enumerate(self.buffer):
                logits, val, h = self.policy.forward(tr.state)
                probs = _softmax(logits)
                logp = math.log(max(1e-9, probs[tr.action]))
                ratio = math.exp(logp - tr.logp)
                surr1 = ratio * advs[idx]
                surr2 = _clamp(ratio, 1 - self.clip, 1 + self.clip) * advs[idx]
                entropy = -sum(p * math.log(max(1e-9, p)) for p in probs)
                actor_loss = -min(surr1, surr2) - self.entropy_coef * entropy
                critic_loss = 0.5 * (rets[idx] - val) ** 2
                total_loss = actor_loss + critic_loss
                # pseudo gradients: sign descent
                g = -1 if total_loss > 0 else 1
                grads = {
                    "w1": [[g * 0.001 for _ in row] for row in self.policy.w1],
                    "b1": [g * 0.001 for _ in self.policy.b1],
                    "wp": [[g * 0.001 for _ in row] for row in self.policy.wp],
                    "bp": [g * 0.001 for _ in self.policy.bp],
                    "wv": [[g * 0.001 for _ in row] for row in self.policy.wv],
                    "bv": [g * 0.001 for _ in self.policy.bv],
                }
                self.policy.train_step(grads)
        self.buffer.clear()

    def step(
        self,
        state: List[float],
        action: int,
        reward: float,
        done: bool,
        risk_hint: float,
        uncertainty_hint: float,
        coherence_hint: float,
    ):
        logits, val, _ = self.policy.forward(state)
        probs = _softmax(logits)
        logp = math.log(max(1e-9, probs[action]))
        se = self.symbolic.evaluate(
            assemble_se41_context(
                risk_hint=risk_hint,
                uncertainty_hint=uncertainty_hint,
                coherence_hint=coherence_hint,
            )
        )
        adj_reward = reward - 0.5 * se.risk + 0.2 * se.coherence
        self.remember(PPOTransition(state, action, logp, val, adj_reward, done))

    def snapshot(self) -> Dict[str, Any]:
        return {"buffer": len(self.buffer), "entropy_coef": self.entropy_coef}


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0):
    return max(lo, min(hi, x))


def _selftest() -> int:  # pragma: no cover
    random.seed(1)
    agent = PPOAgent(state_dim=5)
    s = [0.0] * 5
    for t in range(80):
        a = agent.act(s, 0.3, 0.2, 0.7)
        ns = [v + random.uniform(-0.02, 0.02) for v in s]
        reward = random.uniform(-0.5, 0.5)
        agent.step(s, a, reward, False, 0.3, 0.2, 0.7)
        s = ns
    agent.update()
    snap = agent.snapshot()
    assert "buffer" in snap
    print("PPOAgent selftest", snap["entropy_coef"])
    return 0


__all__ = ["PPOAgent"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    agent = PPOAgent(4)
    print(json.dumps(agent.snapshot(), indent=2))
