"""Scenario application helpers (SE41 v4.1+ enhanced)

Added:
	* Severity + probability blended numeric gating
	* Optional context assembly stub
	* Latency (aggregate) for batch apply if desired by caller (exposed via result list length only here; no global object state)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Iterable, Optional, Any

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
        return {"substrate": {"S_EM": 0.83}}


@dataclass
class ScenarioSpec:
    name: str
    shock_pct: float  # applied multiplicatively (1 + shock_pct)
    probability: float = 1.0


@dataclass
class ScenarioResult:
    name: str
    adjusted_prices: Dict[str, float]
    decision: str


def apply_scenarios(
    prices: Dict[str, float],
    scenarios: Iterable[ScenarioSpec],
    use_context: bool = False,
    ctx_seed: Optional[Dict[str, Any]] = None,
) -> List[ScenarioResult]:
    if use_context:
        if ctx_seed is None:
            ctx_seed = {"substrate": {"S_EM": 0.86}, "intent": {"mode": "scenario"}}
        ctx = assemble_se41_context(**ctx_seed)
    else:
        ctx = None
    results: List[ScenarioResult] = []
    for sc in scenarios:
        magnitude = abs(sc.shock_pct)
        numeric = se41_numeric(
            M_t=0.58, DNA_states=[1.0, magnitude, sc.probability, 1.06]
        )
        base_score = numeric.get("score", 0.55)
        if ctx is not None:
            coh = se41_signals(ctx).get("coherence", 0.55)
            score = (base_score + coh) / 2.0
        else:
            score = base_score
        gate = ethos_decision({"scope": "scenario", "mag": magnitude, "score": score})
        decision = gate.get("decision", "allow") if isinstance(gate, dict) else "allow"
        if decision == "deny":
            results.append(ScenarioResult(sc.name, {}, "deny"))
            continue
        adjusted = {sym: px * (1.0 + sc.shock_pct) for sym, px in prices.items()}
        results.append(ScenarioResult(sc.name, adjusted, decision))
    return results


__all__ = ["ScenarioSpec", "ScenarioResult", "apply_scenarios"]
