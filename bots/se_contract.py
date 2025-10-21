"""Shared contract helpers for SE-aware bots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from symbolic_core.se_loader_ext import load_se_engine


@dataclass
class SEContext:
    """Normalized symbolic context exposed to trading bots."""

    coherence: float
    impetus: float
    risk: float
    uncertainty: float
    wings: float
    reality_alignment: float
    gate12: float
    readiness: str
    gamma: float
    gate12_array: List[float]


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_se_context() -> SEContext:
    """Load the active symbolic engine and normalize its signals."""

    signals = load_se_engine()
    return SEContext(
        coherence=_float(getattr(signals, "coherence", 0.0)),
        impetus=_float(getattr(signals, "impetus", 0.0)),
        risk=_float(getattr(signals, "risk", 1.0), 1.0),
        uncertainty=_float(getattr(signals, "uncertainty", 0.0)),
        wings=_float(getattr(signals, "wings", 1.0), 1.0),
        reality_alignment=_float(getattr(signals, "reality_alignment", getattr(signals, "ra", 0.0))),
        gate12=_float(getattr(signals, "gate12", 1.0), 1.0),
        readiness=str(getattr(signals, "readiness", "warming")),
        gamma=_float(getattr(signals, "gamma", 0.0)),
        gate12_array=list(getattr(signals, "gate12_array", []) or [1.0] * 12)[:12],
    )


def se_guard(context: SEContext, policy: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate the symbolic context against the provided policy."""

    reasons: List[str] = []
    min_ra = _float(policy.get("min_RA", 0.90), 0.90)
    max_risk = _float(policy.get("max_risk", 0.20), 0.20)

    if context.readiness not in {"ready", "prime_ready"}:
        reasons.append("se_not_ready")
        return False, reasons
    if context.reality_alignment < min_ra:
        reasons.append("ra_low")
        return False, reasons
    if context.risk > max_risk:
        reasons.append("risk_high")
        return False, reasons

    reasons.extend(["se_ready", "ra_ok", "risk_ok"])
    return True, reasons
