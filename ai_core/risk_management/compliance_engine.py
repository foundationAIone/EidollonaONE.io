"""Compliance Rule Engine (SE41)

What
----
Validates portfolio & risk metrics against declared policy constraints:
 - Max leverage
 - Position concentration
 - Forbidden symbols
 - VaR / Loss thresholds

Why
---
1. Enforces governance & capital discipline.
2. Breaches escalate risk & uncertainty, reduce coherence.
3. Deterministic rule evaluation for audit & CI.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

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


@dataclass
class ComplianceConfig:
    max_leverage: float = 5.0
    max_concentration: float = 0.3  # single position share of gross exposure
    forbidden_symbols: Optional[List[str]] = None
    var_limit: float = 0.08  # 99% VaR fraction of gross
    stress_loss_limit: float = 0.25  # worst stress loss / gross


@dataclass
class ComplianceResult:
    breaches: List[str]
    stability: float
    se41: SE41Signals
    explain: str


class ComplianceEngine:
    def __init__(
        self,
        config: ComplianceConfig = ComplianceConfig(),
        symbolic: Optional[SymbolicEquation41] = None,
    ) -> None:
        self.config = config
        self.symbolic = symbolic or SymbolicEquation41()

    def evaluate(
        self,
        positions: List[Dict[str, Any]],
        gross_exposure: float,
        leverage: float,
        var_99: float,
        worst_stress_loss: float,
        ctx: Optional[Dict[str, Any]] = None,
    ) -> ComplianceResult:
        """Evaluate compliance constraints and produce SE41-aligned signals.

        Ethos/Alignment: breaches elevate risk & uncertainty, reducing coherence; optional
        ctx allows governance layer to feed additional alignment modifiers.
        """
        breaches: List[str] = []
        cfg = self.config
        if leverage > cfg.max_leverage:
            breaches.append(f"leverage>{cfg.max_leverage}")
        if gross_exposure > 0:
            for p in positions:
                if p["value"] / gross_exposure > cfg.max_concentration:
                    breaches.append(f"concentration:{p['symbol']}")
        if cfg.forbidden_symbols:
            forb = set(cfg.forbidden_symbols)
            for p in positions:
                if p["symbol"] in forb:
                    breaches.append(f"forbidden:{p['symbol']}")
        if var_99 > cfg.var_limit * gross_exposure:
            breaches.append("var_limit")
        if worst_stress_loss > cfg.stress_loss_limit * gross_exposure:
            breaches.append("stress_limit")
        breach_count = len(breaches)
        risk_hint = _clamp01(0.1 + breach_count * 0.15)
        uncertainty_hint = _clamp01(0.2 + breach_count * 0.1)
        coherence_hint = _clamp01(0.95 - breach_count * 0.2)
        se = self.symbolic.evaluate(
            assemble_se41_context(
                risk_hint=risk_hint,
                uncertainty_hint=uncertainty_hint,
                coherence_hint=coherence_hint,
                extras={"compliance": {"breaches": breach_count}, **(ctx or {})},
            )
        )
        stability = _clamp01(1 - (se.risk + se.uncertainty) / 2.0)
        explain = f"breaches={breach_count}" if breach_count else "clean"
        return ComplianceResult(breaches, stability, se, explain)

    def snapshot_dict(self, *a, **kw) -> Dict[str, Any]:
        r = self.evaluate(*a, **kw)
        return {
            "breaches": r.breaches,
            "stability": r.stability,
            "se41": {
                "risk": r.se41.risk,
                "uncertainty": r.se41.uncertainty,
                "coherence": r.se41.coherence,
            },
            "explain": r.explain,
        }


def _selftest() -> int:  # pragma: no cover
    eng = ComplianceEngine()
    positions = [{"symbol": "AAA", "value": 600}, {"symbol": "BBB", "value": 400}]
    d = eng.snapshot_dict(
        positions, 1000, leverage=2.0, var_99=10, worst_stress_loss=50
    )
    assert "breaches" in d
    print("ComplianceEngine selftest", d["explain"])
    return 0


__all__ = ["ComplianceEngine", "ComplianceConfig", "ComplianceResult"]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    ce = ComplianceEngine()
    print(
        json.dumps(
            ce.snapshot_dict(
                [{"symbol": "X", "value": 300}],
                300,
                leverage=1.2,
                var_99=5,
                worst_stress_loss=20,
            ),
            indent=2,
        )
    )
