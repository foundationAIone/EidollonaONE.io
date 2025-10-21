from __future__ import annotations
from typing import Dict, Any, Optional

def assemble_se41_context(
    coherence_hint: float = 0.82,
    risk_hint: float = 0.15,
    uncertainty_hint: float = 0.25,
    mirror_consistency: float = 0.70,
    s_em: float = 0.78,
    t: float = 0.0,
    ethos_hint: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    return {
        "coherence_hint": float(coherence_hint),
        "risk_hint": float(risk_hint),
        "uncertainty_hint": float(uncertainty_hint),
        "mirror": {"consistency": float(mirror_consistency)},
        "substrate": {"S_EM": float(s_em)},
        "ethos_hint": ethos_hint or {},
        "t": float(t) % 1.0,
    }
