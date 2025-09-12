"""Trade signal generation module (SymbolicEquation41 enhanced).

Generates BUY/SELL/HOLD signals by mapping SE41Signals (impetus, risk,
uncertainty) plus simple market feature engineering (volatility, trend).

Deterministic, side‑effect free logic for easy testing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, List

from symbolic_core.symbolic_equation import SymbolicEquation41, SE41Signals
from symbolic_core.context_builder import assemble_se41_context


@dataclass
class SignalResult:
    action: str  # BUY / SELL / HOLD
    confidence: float  # 0..1 aggregated confidence
    size_factor: float  # 0..1 suggested position size scaler
    se41: SE41Signals  # raw symbolic signals
    explain: str  # human readable rationale
    features: Dict[str, float]


class TradeSignalEngine:
    def __init__(self, symbolic: Optional[SymbolicEquation41] = None) -> None:
        self.symbolic = symbolic or SymbolicEquation41()

    # -----------------
    # Feature building
    # -----------------
    def build_features(self, prices: List[float]) -> Dict[str, float]:
        if not prices or len(prices) < 2:
            return {"volatility": 0.0, "trend": 0.0, "momentum": 0.0}
        # Simple % changes
        changes = [0.0]
        for a, b in zip(prices[:-1], prices[1:]):
            try:
                changes.append((b - a) / a if a else 0.0)
            except Exception:
                changes.append(0.0)
        # Volatility = std-like proxy
        import statistics

        try:
            vol = float(min(1.0, abs(statistics.pstdev(changes)) * 10.0))
        except Exception:
            vol = 0.0
        trend = float(sum(changes[-5:]))  # last window cumulative change
        momentum = float(changes[-1])
        # Clamp to [-1,1]
        clamp = lambda x: max(-1.0, min(1.0, x))
        return {
            "volatility": clamp(vol),
            "trend": clamp(trend),
            "momentum": clamp(momentum),
        }

    # -----------------
    # Core evaluation
    # -----------------
    def evaluate(
        self,
        prices: List[float],
        extras: Optional[Dict[str, Any]] = None,
        ctx: Optional[Dict[str, Any]] = None,
    ) -> SignalResult:
        """Generate a trade signal.

        SE41 ethos alignment: coherence, risk, uncertainty shaping; ctx (optional) allows
        callers to pass higher-level governance or alignment metadata.
        """
        features = self.build_features(prices)
        # Map feature domain to hints: high volatility raises uncertainty, negative trend raises risk
        risk_hint = (
            0.12
            + max(0.0, -features["trend"]) * 0.4
            + abs(features["volatility"]) * 0.2
        )
        uncertainty_hint = 0.28 + abs(features["volatility"]) * 0.5
        coherence_hint = 0.80 + features["trend"] * 0.05  # mild trend influence

        ctx_payload = assemble_se41_context(
            coherence_hint=coherence_hint,
            risk_hint=risk_hint,
            uncertainty_hint=uncertainty_hint,
            extras={"market": features, **(extras or {}), **(ctx or {})},
        )
        se = self.symbolic.evaluate(ctx_payload)  # returns SE41Signals

        # Decision heuristic:
        # - BUY if impetus high and risk low, momentum positive
        # - SELL if risk high or momentum strongly negative
        # - else HOLD
        impetus = se.impetus
        risk = se.risk
        momentum = features["momentum"]

        action = "HOLD"
        rationale = []
        size_factor = impetus * (1.0 - risk)

        if impetus > 0.55 and risk < 0.35 and momentum > 0.0:
            action = "BUY"
            rationale.append("impetus>0.55 & risk<0.35 & positive momentum")
        elif risk > 0.50 or momentum < -0.03:
            action = "SELL"
            rationale.append("risk>0.50 or strong negative momentum")
        else:
            rationale.append("conditions neutral -> HOLD")

        confidence = max(
            0.0, min(1.0, (se.coherence + (1 - risk) + abs(momentum)) / 3.0)
        )

        return SignalResult(
            action=action,
            confidence=confidence,
            size_factor=max(0.0, min(1.0, size_factor)),
            se41=se,
            explain="; ".join(rationale),
            features=features,
        )


__all__ = ["TradeSignalEngine", "SignalResult"]
