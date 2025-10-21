from typing import Any, Dict, Optional, Tuple, cast, List

try:
    # Prefer analyzer-visible shim that exports SymbolicEquation41
    from symbolic_core.symbolic_equation41 import (
        SymbolicEquation41,
        SE41Signals,
    )  # type: ignore
except Exception:
    SymbolicEquation41 = None  # type: ignore
    SE41Signals = None  # type: ignore

try:
    from symbolic_core.context_builder import assemble_se41_context
except Exception:

    def assemble_se41_context(*args, **kwargs):  # type: ignore[override]
        import time

        return {
            "mirror": {"consistency": 0.7},
            "coherence_hint": 0.81,
            "risk_hint": 0.12,
            "uncertainty_hint": 0.28,
            "substrate": {"S_EM": 0.83},
            "t": (time.time() % 60.0) / 60.0,
        }


def se41_signals(*args: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
    """
    Return SE41Signals as dict-like or None if unavailable.

    Backward/forward compatible: if a single dict payload is provided, echo it
    back as the "features" envelope with a default confidence, so callers that
    pass in lightweight context don't fail even if the live SE41 engine isn't used.
    """
    try:
        # If caller provided a dict payload, accept it and wrap minimally
        if args and isinstance(args[0], dict):
            d = cast(Dict[str, Any], args[0])
            out: Dict[str, Any] = {"features": d, "confidence": d.get("confidence", 0.5)}
            return out
        if SymbolicEquation41 is None:
            return None
        se = SymbolicEquation41()
        sig = se.evaluate(assemble_se41_context())  # type: ignore[arg-type]
        return cast(Dict[str, Any], getattr(sig, "__dict__", sig))
    except Exception:
        return None


def ethos_decision(tx: Dict[str, Any]) -> Tuple[str, str]:
    """Return (decision, reason) where decision in {allow,hold,deny,redirect}."""
    try:
        from finance.policy.ethos_gate import ethos_gate  # type: ignore
    except Exception:
        return ("allow", "ethos_missing")
    s = se41_signals()
    if not s:
        return ("hold", "no_se41_signals")
    try:
        return ethos_gate(s, tx or {})  # type: ignore
    except Exception:
        return ("hold", "ethos_exception")


def ethos_decision_envelope(tx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a dict envelope for ethos decision with keys:
      { 'decision': 'allow'|'hold'|'deny'|'redirect', 'reason': str, 'pillars': {...} }

    - Backward compatible with tuple-returning ethos_decision; we adapt into a dict.
    - Pillars are derived from tx['ethos'] if present; otherwise from latest se41_signals().
    - Safe defaults provided to support SAFE posture when signals are unavailable.
    """
    try:
        decision, reason = ethos_decision(tx)
    except Exception:
        decision, reason = ("hold", "ethos_exception")

    # Prefer pillars from the provided transaction payload
    pillars: Dict[str, float] = {}
    try:
        if isinstance(tx, dict) and isinstance(tx.get("ethos"), dict):
            eth = cast(Dict[str, Any], tx.get("ethos", {}))
            pillars = {
                "authenticity": float(eth.get("authenticity", 0.0)),
                "integrity": float(eth.get("integrity", 0.0)),
                "responsibility": float(eth.get("responsibility", 0.0)),
                "enrichment": float(eth.get("enrichment", 0.0)),
            }
        else:
            # fallback to pillars from last signals packet
            s = se41_signals() or {}
            eth2 = cast(Dict[str, Any], s.get("ethos", {})) if isinstance(s, dict) else {}
            pillars = {
                "authenticity": float(eth2.get("authenticity", 0.0)),
                "integrity": float(eth2.get("integrity", 0.0)),
                "responsibility": float(eth2.get("responsibility", 0.0)),
                "enrichment": float(eth2.get("enrichment", 0.0)),
            }
    except Exception:
        pillars = {"authenticity": 0.0, "integrity": 0.0, "responsibility": 0.0, "enrichment": 0.0}

    return {"decision": decision, "reason": reason, "pillars": pillars}


def se41_numeric(
    M_t: Optional[float] = None,
    DNA_states: Optional[List[float]] = None,
    harmonic_patterns: Optional[List[float]] = None,
) -> float:
    """
    Return a composite numeric magnitude derived from SE41 signals (0-100).

    Backward-compatible signature: optional parameters are accepted and ignored.
    """
    s = se41_signals()
    if not s:
        return 0.0
    try:
        coherence = float(s.get("coherence", 0.5))
        risk = float(s.get("risk", 0.5))
        impetus = float(s.get("impetus", 0.5))
        return ((coherence + (1 - risk) + impetus) / 3.0) * 100.0
    except Exception:
        return 0.0


__all__ = [
    "se41_signals",
    "ethos_decision",
    "ethos_decision_envelope",
    "se41_numeric",
]
