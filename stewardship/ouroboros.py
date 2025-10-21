from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import time

try:
    from symbolic_core.se41_ext import clamp01 as _se41_clamp01
    from symbolic_core.se41_ext import ouroboros_score as _se41_ouroboros_score
    from symbolic_core.se41_ext import road_map as _se41_road_map

    def clamp01(value: float) -> float:
        return float(_se41_clamp01(value))

    def ouroboros_score(metrics: Dict[str, float]) -> float:
        return float(_se41_ouroboros_score(metrics))

    def road_map(
        coherence: float,
        impetus: float,
        risk: float,
        uncertainty: float,
        ouro: float,
    ) -> Dict[str, str]:
        return _se41_road_map(
            coherence=coherence,
            impetus=impetus,
            risk=risk,
            uncertainty=uncertainty,
            ouro=ouro,
        )

except Exception:  # pragma: no cover - development fallback

    def clamp01(value: float) -> float:
        try:
            numeric = float(value)
        except Exception:
            return 0.0
        if numeric < 0.0:
            return 0.0
        if numeric > 1.0:
            return 1.0
        return numeric

    def ouroboros_score(metrics: Dict[str, float]) -> float:
        waste = clamp01(metrics.get("waste", 0.0))
        oscillation = clamp01(metrics.get("oscillation", 0.0))
        stasis = clamp01(metrics.get("stasis", 0.0))
        novelty = clamp01(metrics.get("novelty", 1.0))
        return clamp01(0.35 * waste + 0.30 * oscillation + 0.20 * stasis + 0.15 * (1.0 - novelty))

    def road_map(coherence: float, impetus: float, risk: float, uncertainty: float, ouro: float) -> Dict[str, str]:
        coherence = clamp01(coherence)
        impetus = clamp01(impetus)
        risk = clamp01(risk)
        uncertainty = clamp01(uncertainty)
        ouro = clamp01(ouro)
        if coherence >= 0.75 and risk <= 0.20 and ouro <= 0.35:
            return {"sovereign_gate": "ROAD", "gate": "ALLOW"}
        if coherence >= 0.60 and risk <= 0.35 and ouro <= 0.55:
            return {"sovereign_gate": "SHOULDER", "gate": "REVIEW"}
        return {"sovereign_gate": "OFFROAD", "gate": "HOLD"}

try:
    from utils.audit import audit_ndjson as _audit
except Exception:  # pragma: no cover - development fallback

    def _audit(event: str, **payload: Any) -> None:
        return None


_WEIGHTS: Dict[str, float] = {
    "waste": 0.35,
    "oscillation": 0.30,
    "stasis": 0.20,
    "novelty": -0.15,
}

_TIERS = [
    (0.15, "none"),
    (0.35, "low"),
    (0.55, "moderate"),
    (0.75, "high"),
    (1.00, "critical"),
]


@dataclass
class OuroborosReport:
    score: float
    tier: str
    origin: str
    contributors: List[str]
    recommendations: List[str]
    metrics: Dict[str, float]
    ts: float
    sovereign_gate: Optional[str] = None
    gate: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _normalize_metrics(raw: Dict[str, float]) -> Dict[str, float]:
    normalized: Dict[str, float] = {}
    for key in ("waste", "oscillation", "stasis", "novelty"):
        normalized[key] = clamp01(float(raw.get(key, 0.0)))
    return normalized


def _tier(score: float) -> str:
    for threshold, label in _TIERS:
        if score <= threshold:
            return label
    return "critical"


def _contributions(metrics: Dict[str, float]) -> Dict[str, float]:
    contributions: Dict[str, float] = {}
    for key, weight in _WEIGHTS.items():
        if key == "novelty":
            contributions[key] = weight * (1.0 - metrics.get(key, 0.0))
        else:
            contributions[key] = weight * metrics.get(key, 0.0)
    return contributions


def _recommendations(score: float, tier: str) -> List[str]:
    if tier in ("critical", "high"):
        return [
            "Enter REVIEW/HOLD: stop new expansion, reduce waste and oscillation immediately.",
            "Run resilience drill in the EMP resonance body; lower noise, raise smoothness.",
            "Use EMP-Guard drill and ethos rebind on drifting services; restart in SAFE.",
        ]
    if tier == "moderate":
        return [
            "Proceed cautiously: shorten loops, cap runtime/cost, and re-check SE41 after a short paper run.",
            "Increase novelty safely to break the loop.",
        ]
    if tier == "low":
        return ["Maintain vigilance: log loop hotspots; schedule a light resilience check this cycle."]
    return ["No actionable loop detected: continue normal operation with periodic checks."]


def diagnose(loop_metrics: Dict[str, float]) -> Dict[str, Any]:
    origin = str(loop_metrics.get("origin", "unknown"))
    metrics = _normalize_metrics(loop_metrics)
    score = ouroboros_score(metrics)
    tier = _tier(score)
    contributions = _contributions(metrics)
    ranking = sorted(contributions.items(), key=lambda item: abs(item[1]), reverse=True)
    top_contributors = [key for key, _ in ranking[:3]]
    recommendations = _recommendations(score, tier)

    report = OuroborosReport(
        score=score,
        tier=tier,
        origin=origin,
        contributors=top_contributors,
        recommendations=recommendations,
        metrics=metrics,
        ts=time.time(),
    )
    _audit("ouroboros_diagnose", metrics=metrics, origin=origin, score=score, tier=tier, top=top_contributors)
    return report.to_dict()


def diagnose_with_se41(
    loop_metrics: Dict[str, float],
    signals: Dict[str, float],
    *,
    ouroboros_override: Optional[float] = None,
) -> Dict[str, Any]:
    base = diagnose(loop_metrics)
    ouro_value = clamp01(float(ouroboros_override)) if ouroboros_override is not None else clamp01(base["score"])
    coherence = float(signals.get("coherence", 0.0))
    impetus = float(signals.get("impetus", 0.0))
    risk = float(signals.get("risk", 1.0))
    uncertainty = float(signals.get("uncertainty", 1.0))
    gate_map = road_map(coherence, impetus, risk, uncertainty, ouro_value)

    base["sovereign_gate"] = gate_map["sovereign_gate"]
    base["gate"] = gate_map["gate"]
    _audit(
        "ouroboros_diagnose_se41",
        score=ouro_value,
        signals={
            "coherence": coherence,
            "impetus": impetus,
            "risk": risk,
            "uncertainty": uncertainty,
        },
        gate=gate_map,
    )
    return base


__all__ = [
    "OuroborosReport",
    "diagnose",
    "diagnose_with_se41",
]
