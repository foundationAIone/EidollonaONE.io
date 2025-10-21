from __future__ import annotations

from typing import Dict, Iterable

__all__ = [
    "clamp01",
    "ethos_avg",
    "ouroboros_score",
    "road_map",
    "FOUR_PILLARS",
]


def clamp01(value: float) -> float:
    """Coerce *value* into the inclusive range [0, 1]."""

    try:
        numeric = float(value)
    except Exception:
        return 0.0
    if numeric < 0.0:
        return 0.0
    if numeric > 1.0:
        return 1.0
    return numeric


FOUR_PILLARS: Iterable[str] = (
    "authenticity",
    "integrity",
    "responsibility",
    "enrichment",
)


def ethos_avg(ethos: Dict[str, float]) -> float:
    """Return a SAFE-guarded average of SE41 ethos pillars."""

    if not ethos:
        return 0.0
    values = [float(ethos.get(pillar, 0.0)) for pillar in FOUR_PILLARS]
    mean = sum(values) / max(1, len(values))
    return clamp01(mean)


def ouroboros_score(metrics: Dict[str, float]) -> float:
    """
    Compute a [0, 1] heuristic for tail-eating feedback loops.

    Heavier weight is assigned to *waste* and *oscillation*, moderate to
    *stasis*, and penalization for higher *novelty* (less ouroboros risk).
    Missing metrics default to SAFE neutral values.
    """

    waste = clamp01(metrics.get("waste", 0.0))
    oscillation = clamp01(metrics.get("oscillation", 0.0))
    stasis = clamp01(metrics.get("stasis", 0.0))
    novelty = clamp01(metrics.get("novelty", 1.0))
    score = 0.35 * waste + 0.30 * oscillation + 0.20 * stasis + 0.15 * (1.0 - novelty)
    return clamp01(score)


def road_map(coherence: float, impetus: float, risk: float, uncertainty: float, ouro: float) -> Dict[str, str]:
    """Map SE41 signals to sovereign gate states (ROAD/SHOULDER/OFFROAD)."""

    coh = clamp01(coherence)
    imp = clamp01(impetus)
    unk = clamp01(uncertainty)
    risk_val = clamp01(risk)
    ouro_val = clamp01(ouro)

    if coh >= 0.75 and risk_val <= 0.20 and ouro_val <= 0.35:
        return {"sovereign_gate": "ROAD", "gate": "ALLOW"}
    if (
        coh >= 0.60
        and risk_val <= 0.35
        and ouro_val <= 0.55
        and imp >= 0.30
        and unk <= 0.55
    ):
        return {"sovereign_gate": "SHOULDER", "gate": "REVIEW"}
    return {"sovereign_gate": "OFFROAD", "gate": "HOLD"}
