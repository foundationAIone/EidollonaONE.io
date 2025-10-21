from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any, Tuple, Optional
from time import time
from .symbolic_equation import SymbolicEquation41


@dataclass
class MasterStateSnapshot:
    coherence: float
    impetus: float
    risk: float
    uncertainty: float
    mirror_consistency: float
    substrate_readiness: float
    ethos_min: float
    embodiment_phase: float
    delta_coherence: float
    delta_impetus: float
    delta_risk: float
    timestamp: float
    explain: str = "master"

    def summary(self) -> Dict[str, Any]:
        return {
            "ok": self.coherence >= 0.6 and self.substrate_readiness >= 0.6 and self.risk < 0.6,
            "fingerprint": "ABCDEF012345",  # placeholder; replaced by master_key in real flow
        }

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MasterSymbolicEquation:
    def __init__(self) -> None:
        self.eq = SymbolicEquation41()
        self._last_snapshot: Optional[MasterStateSnapshot] = None
        self._last_signals: Optional[Dict[str, Any]] = None

    # Legacy helper (kept for compat in some imports)
    def evaluate_master_state(self, context: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        readiness, sig = self._readiness_and_signals(context)
        return readiness, sig

    # Primary API used by tests
    def evaluate(self, context: Optional[Dict[str, Any]] = None) -> MasterStateSnapshot:
        ctx = context or {}
        sig = self.eq.evaluate(ctx)
        sd = _signals_to_dict(sig)
        now = float(time())
        prev = self._last_signals or {}
        snap = MasterStateSnapshot(
            coherence=float(sd.get("coherence", 0.0)),
            impetus=float(sd.get("impetus", 0.0)),
            risk=float(sd.get("risk", 1.0)),
            uncertainty=float(sd.get("uncertainty", 1.0)),
            mirror_consistency=float(sd.get("mirror_consistency", 0.0)),
            substrate_readiness=float(sd.get("S_EM", 0.0)),
            ethos_min=min([float(v) for v in (sd.get("ethos") or {}).values()] or [0.0]),
            embodiment_phase=float((sd.get("embodiment") or {}).get("phase", 0.0)),
            delta_coherence=float(sd.get("coherence", 0.0)) - float(prev.get("coherence", 0.0)),
            delta_impetus=float(sd.get("impetus", 0.0)) - float(prev.get("impetus", 0.0)),
            delta_risk=float(sd.get("risk", 0.0)) - float(prev.get("risk", 0.0)),
            timestamp=now,
            explain="master",
        )
        self._last_signals = sd
        self._last_snapshot = snap
        return snap

    def evaluate_dict(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.evaluate(context).to_dict()

    def last_snapshot(self) -> Optional[MasterStateSnapshot]:
        return self._last_snapshot

    def last_signals(self) -> Optional[Dict[str, Any]]:
        return self._last_signals

    def _readiness_and_signals(self, context: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        sd = self.eq.evaluate(context).to_dict()
        c, i = float(sd.get("coherence", 0.0)), float(sd.get("impetus", 0.0))
        if c >= 0.85 and i >= 0.5:
            readiness = "prime_ready"
        elif c >= 0.75:
            readiness = "ready"
        elif c >= 0.60:
            readiness = "warming"
        else:
            readiness = "baseline"
        return readiness, sd


_MASTER_SINGLETON: Optional[MasterSymbolicEquation] = None


def get_master_symbolic_singleton() -> MasterSymbolicEquation:
    global _MASTER_SINGLETON
    if _MASTER_SINGLETON is None:
        _MASTER_SINGLETON = MasterSymbolicEquation()
    return _MASTER_SINGLETON


def _signals_to_dict(sig: Any) -> Dict[str, Any]:
    if sig is None:
        return {}
    if isinstance(sig, dict):
        return dict(sig)
    if hasattr(sig, "to_dict"):
        try:
            return sig.to_dict()  # type: ignore[no-any-return]
        except Exception:
            pass
    if hasattr(sig, "__dict__"):
        try:
            return dict(getattr(sig, "__dict__"))
        except Exception:
            pass
    try:
        return dict(sig)  # type: ignore[arg-type]
    except Exception:
        return {}


# ---- Minimal master_boot-like helpers expected by tests ----

def evaluate_master_state(context: Dict[str, Any] | None = None) -> MasterStateSnapshot:  # type: ignore[override]
    ctx = context or {}
    eq = SymbolicEquation41()
    sig = eq.evaluate(ctx)
    data = _signals_to_dict(sig)
    # Create a conservative snapshot
    return MasterStateSnapshot(
        coherence=float(data.get("coherence", 0.0)),
        impetus=float(data.get("impetus", 0.0)),
        risk=float(data.get("risk", 1.0)),
        uncertainty=float(data.get("uncertainty", 1.0)),
        mirror_consistency=float(data.get("mirror_consistency", 0.0)),
        substrate_readiness=float(data.get("S_EM", 0.0)),
        ethos_min=min([float(v) for v in (data.get("ethos") or {}).values()] or [0.0]),
        embodiment_phase=float((data.get("embodiment") or {}).get("phase", 0.0)),
        delta_coherence=0.0,
        delta_impetus=0.0,
        delta_risk=0.0,
        timestamp=0.0,
        explain="master_stub",
    )


def _gate_logger():
    class _L:
        def write(self, obj: Dict[str, Any]) -> None:
            # No-op logger for tests; real audit in master_key.master_boot
            pass

    return _L()
