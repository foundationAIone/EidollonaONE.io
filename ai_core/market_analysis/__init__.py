"""Market Analysis Suite

Exports advanced analytics engines:
 - SentimentEngine: stream sentiment polarity, momentum, dispersion, consensus
 - AnomalyDetector: price & volume anomaly pressure (z, MAD, envelope)
 - VolumeAnalyzer: participation, imbalance, VWAP deviation, burst score
 - MarketProfile: volume-at-price (POC, VAH/VAL, kurtosis, balance)
 - OrderFlowAnalyzer: cumulative delta, imbalance, absorption, micro pressure
 - PriceActionAnalyzer: regime (trend/mean-revert/chaotic), structure & volatility

Includes optional CompositeMarketAnalysis aggregator producing a unified SE41
snapshot by blending underlying engines (simple weighted approach).
"""

from __future__ import annotations
from typing import Optional, Dict, Any

from .sentiment_analysis import SentimentEngine
from .anomaly_detector import AnomalyDetector
from .volume_analysis import VolumeAnalyzer
from .market_profile import MarketProfile
from .order_flow import OrderFlowAnalyzer
from .price_action import PriceActionAnalyzer

try:  # pragma: no cover
    from symbolic_core.symbolic_equation41 import SymbolicEquation41  # type: ignore
    from symbolic_core.se41_context import assemble_se41_context  # type: ignore
except Exception:  # pragma: no cover

    class SymbolicEquation41:  # type: ignore
        def evaluate(self, ctx):
            class S:
                pass

            s = S()
            s.risk = ctx.get("risk_hint", 0.4)
            s.uncertainty = ctx.get("uncertainty_hint", 0.4)
            s.coherence = ctx.get("coherence_hint", 0.6)
            return s

    def assemble_se41_context(**kw):
        return kw


def _blend(values):
    return sum(values) / max(1, len(values))


class CompositeMarketAnalysis:
    def __init__(self, symbolic: Optional[SymbolicEquation41] = None):
        self.sentiment = SentimentEngine(symbolic=symbolic)
        self.anomaly = AnomalyDetector(symbolic=symbolic)
        self.volume = VolumeAnalyzer(symbolic=symbolic)
        self.profile = MarketProfile(symbolic=symbolic)
        self.order_flow = OrderFlowAnalyzer(symbolic=symbolic)
        self.price_action = PriceActionAnalyzer(symbolic=symbolic)
        self.symbolic = symbolic or SymbolicEquation41()

    def snapshot(self) -> Dict[str, Any]:
        s_sent = self.sentiment.snapshot_dict()
        s_anom = self.anomaly.snapshot_dict()
        s_vol = self.volume.snapshot_dict()
        s_prof = self.profile.snapshot_dict()
        s_of = self.order_flow.snapshot_dict()
        s_pa = self.price_action.snapshot_dict()
        risks = [
            s_sent["se41"]["risk"],
            s_anom["se41"]["risk"],
            s_vol["se41"]["risk"],
            s_prof["se41"]["risk"],
            s_of["se41"]["risk"],
            s_pa["se41"]["risk"],
        ]
        uncs = [
            s_sent["se41"]["uncertainty"],
            s_anom["se41"]["uncertainty"],
            s_vol["se41"]["uncertainty"],
            s_prof["se41"]["uncertainty"],
            s_of["se41"]["uncertainty"],
            s_pa["se41"]["uncertainty"],
        ]
        cohs = [
            s_sent["se41"]["coherence"],
            s_anom["se41"]["coherence"],
            s_vol["se41"]["coherence"],
            s_prof["se41"]["coherence"],
            s_of["se41"]["coherence"],
            s_pa["se41"]["coherence"],
        ]
        risk_hint = _blend(risks)
        uncertainty_hint = _blend(uncs)
        coherence_hint = _blend(cohs)
        se = self.symbolic.evaluate(
            assemble_se41_context(
                risk_hint=risk_hint,
                uncertainty_hint=uncertainty_hint,
                coherence_hint=coherence_hint,
                extras={"composite": {"engines": 6}},
            )
        )
        stability = max(0.0, min(1.0, 1.0 - (se.risk + se.uncertainty) / 2.0))
        return {
            "engines": {
                "sentiment": s_sent,
                "anomaly": s_anom,
                "volume": s_vol,
                "profile": s_prof,
                "order_flow": s_of,
                "price_action": s_pa,
            },
            "se41": {
                "risk": se.risk,
                "uncertainty": se.uncertainty,
                "coherence": se.coherence,
            },
            "stability": stability,
        }


__all__ = [
    "SentimentEngine",
    "AnomalyDetector",
    "VolumeAnalyzer",
    "MarketProfile",
    "OrderFlowAnalyzer",
    "PriceActionAnalyzer",
    "CompositeMarketAnalysis",
]
