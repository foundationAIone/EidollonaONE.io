from typing import Dict, Any, Optional


def assemble_se41_context(
    coherence_hint: float = 0.81,
    risk_hint: float = 0.12,
    uncertainty_hint: float = 0.28,
    mirror_consistency: float = 0.74,
    s_em: float = 0.83,
    phase: float = 0.0,
    cadence_spm: float = 108.0,
    step_len_m: float = 0.65,
    extras: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Centralized assembly for SymbolicEquation41 evaluation context.

    Callers can override any default or pass an extras dict merged shallowly.
    """
    ctx: Dict[str, Any] = {
        "coherence_hint": float(coherence_hint),
        "risk_hint": float(risk_hint),
        "uncertainty_hint": float(uncertainty_hint),
        "mirror": {"consistency": float(mirror_consistency)},
        "substrate": {"S_EM": float(s_em)},
        "embodiment": {
            "phase": float(phase),
            "cadence_spm": float(cadence_spm),
            "step_len_m": float(step_len_m),
        },
    }
    if extras:
        ctx.update(extras)
    return ctx


__all__ = ["assemble_se41_context"]
