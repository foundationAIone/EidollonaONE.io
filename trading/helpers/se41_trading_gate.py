from typing import Dict, Any, Tuple

try:
    from symbolic_core.symbolic_equation import (
        SymbolicEquation41,
        SE41Signals,
    )  # repo uses symbolic_equation shim
except Exception:
    SymbolicEquation41 = None  # type: ignore
    SE41Signals = None  # type: ignore

try:
    from symbolic_core.context_builder import assemble_se41_context
except Exception:

    def assemble_se41_context(state=None, extras=None):  # type: ignore
        import time

        return {
            "mirror": {"consistency": 0.7},
            "coherence_hint": 0.81,
            "risk_hint": 0.12,
            "uncertainty_hint": 0.28,
            "substrate": {"S_EM": 0.83},
            "t": (time.time() % 60.0) / 60.0,
        }


def se41_signals() -> Dict[str, Any] | None:
    """Return SE41Signals as dict-like or None if unavailable."""
    try:
        if SymbolicEquation41 is None:
            return None
        se = SymbolicEquation41()
        sig = se.evaluate(assemble_se41_context())  # type: ignore[arg-type]
        return getattr(sig, "__dict__", sig)
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


def se41_numeric() -> float:
    """Return a composite numeric magnitude derived from SE41 signals (0-100)."""
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


__all__ = ["se41_signals", "ethos_decision", "se41_numeric"]
