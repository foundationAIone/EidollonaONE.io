from __future__ import annotations

from typing import Any, Dict

from symbolic_core.se41_ext import clamp01, ethos_avg


def se41_to_field_params(signals: Dict[str, Any]) -> Dict[str, float]:
    coherence = clamp01(signals.get("coherence", 0.0))
    impetus = clamp01(signals.get("impetus", 0.0))
    risk = clamp01(signals.get("risk", 1.0))
    uncertainty = clamp01(signals.get("uncertainty", 1.0))
    mirror_consistency = clamp01(signals.get("mirror_consistency", 0.0))
    substrate = clamp01(signals.get("S_EM", 0.0))
    ethos = ethos_avg(signals.get("ethos") or {})

    smoothness = clamp01(0.5 * coherence + 0.3 * mirror_consistency + 0.2 * (1.0 - uncertainty))
    amplitude = clamp01(0.6 * impetus + 0.4 * substrate)
    noise = clamp01(0.6 * risk + 0.4 * uncertainty)

    return {
        "smoothness": smoothness,
        "amplitude": amplitude,
        "noise": noise,
        "ethos_avg": ethos,
    }


def se41_resilience(signals: Dict[str, Any]) -> float:
    coherence = clamp01(signals.get("coherence", 0.0))
    risk = clamp01(signals.get("risk", 1.0))
    uncertainty = clamp01(signals.get("uncertainty", 1.0))
    mirror_consistency = clamp01(signals.get("mirror_consistency", 0.0))
    substrate = clamp01(signals.get("S_EM", 0.0))
    ethos = ethos_avg(signals.get("ethos") or {})

    resilience = (
        0.28 * coherence
        + 0.22 * (1.0 - risk)
        + 0.15 * (1.0 - uncertainty)
        + 0.15 * mirror_consistency
        + 0.10 * substrate
        + 0.10 * ethos
    )
    return clamp01(resilience)
