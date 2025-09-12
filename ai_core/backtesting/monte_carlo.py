"""Monte Carlo path generation (GBM + Jump/Shock) SE41 v4.1+ enhanced

Enhancements:
	* Optional SE41 context & signal coherence blending
	* Gating of volatility AND shock_scale severity
	* Latency measurement for generation run
	* Deterministic fallback path if helpers absent
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import math
import random
from time import perf_counter

try:
    from trading.helpers.se41_trading_gate import (
        se41_numeric,
        ethos_decision,
        se41_signals,
    )  # type: ignore
except Exception:  # pragma: no cover

    def se41_numeric(**_kw):  # type: ignore
        return {"score": 0.55}

    def ethos_decision(_tx):  # type: ignore
        return {"decision": "allow"}

    def se41_signals(_ctx):  # type: ignore
        return {"coherence": 0.55}


try:
    from symbolic_core.se41_context import assemble_se41_context  # type: ignore
except Exception:  # pragma: no cover

    def assemble_se41_context(**kw):  # type: ignore
        return {"substrate": {"S_EM": 0.84}}


@dataclass
class PathResult:
    path: List[float]
    drift: float
    vol: float
    shocks: int
    ethos_flags: Dict[str, int]


class MonteCarloEngine:
    def __init__(self, seed: Optional[int] = None, use_context: bool = False) -> None:
        self.rng = random.Random(seed)
        self.ethos_flags = {"denies": 0, "holds": 0}
        self.use_context = use_context
        self._ctx: Optional[Dict[str, Any]] = None

    def generate(
        self,
        start: float,
        steps: int,
        drift: float,
        vol: float,
        shock_prob: float = 0.0,
        shock_scale: float = 0.0,
    ) -> PathResult:
        begin = perf_counter()
        if self.use_context and self._ctx is None:
            self._ctx = assemble_se41_context(substrate={"S_EM": 0.85})
        path = [start]
        shocks = 0
        for i in range(steps):
            numeric = se41_numeric(M_t=0.6, DNA_states=[1.0, vol, drift, 1.1])
            base_score = numeric.get("score", 0.55)
            if self._ctx is not None:
                coh = se41_signals(self._ctx).get("coherence", 0.55)
                score = (base_score + coh) / 2.0
            else:
                score = base_score
            # incorporate shock scale into gating
            severity = max(abs(shock_scale), vol)
            gate = ethos_decision(
                {"scope": "mc_step", "vol": vol, "severity": severity, "score": score}
            )
            decision = (
                gate.get("decision", "allow") if isinstance(gate, dict) else "allow"
            )
            if decision == "deny":
                self.ethos_flags["denies"] += 1
                break
            if decision == "hold":
                self.ethos_flags["holds"] += 1
                path.append(path[-1])
                continue
            z = self.rng.normalvariate(0, 1)
            next_price = path[-1] * math.exp((drift - 0.5 * vol * vol) + vol * z)
            if shock_prob > 0 and self.rng.random() < shock_prob:
                shocks += 1
                next_price *= 1.0 + self.rng.uniform(-shock_scale, shock_scale)
            path.append(next_price)
        self.last_latency_ms = round((perf_counter() - begin) * 1000.0, 3)
        return PathResult(path, drift, vol, shocks, dict(self.ethos_flags))


__all__ = ["MonteCarloEngine", "PathResult"]
