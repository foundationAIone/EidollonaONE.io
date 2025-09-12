"""symbolic_equation_master

Facade / adapter on top of SymbolicEquation41 adding:
  - cached signal evaluation
  - lightweight delta tracking (coherence / risk / impetus)
  - helper to produce a normalized master state snapshot consumed by boot
	and awakening phases.

Design goals:
  * Zero external side-effects on import
  * Deterministic, bounded computations (no RNG here)
  * Graceful degradation if v4.1 symbolic core temporarily unavailable
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
import time
import logging

try:  # Prefer explicit v4.1 API
    from symbolic_core.symbolic_equation import SymbolicEquation41, SE41Signals
except Exception:  # pragma: no cover - fallback shim

    class SE41Signals:  # type: ignore
        def __init__(self):
            self.coherence = 0.5
            self.impetus = 0.4
            self.risk = 0.2
            self.uncertainty = 0.3
            self.mirror_consistency = 0.6
            self.S_EM = 0.7
            self.ethos = {}
            self.embodiment = {"phase": 0.0}
            self.explain = "shim"

    class SymbolicEquation41:  # type: ignore
        def evaluate(self, context: Dict[str, Any]):  # noqa: D401
            return SE41Signals()


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
    timestamp: float
    explain: str


class MasterSymbolicEquation:
    """Central symbolic facade.

    Note: This is intentionally thin—keeps a cached last evaluation so that
    multiple subsystems (boot, awakening, planning status endpoints) can query
    the same stable snapshot within a frame / short interval.
    """

    def __init__(self):
        self._sym = SymbolicEquation41()
        self._last_signals: Optional[SE41Signals] = None
        self._last_context: Dict[str, Any] = {}
        self._logger = logging.getLogger(f"{__name__}.MasterSymbolicEquation")

    def evaluate(self, context: Optional[Dict[str, Any]] = None) -> MasterStateSnapshot:
        now = time.time()
        context = context or {}
        # Provide stable defaults if caller only supplies partial hints
        merged = {
            "coherence_hint": context.get("coherence_hint", 0.82),
            "risk_hint": context.get("risk_hint", 0.15),
            "uncertainty_hint": context.get("uncertainty_hint", 0.25),
            "mirror": context.get("mirror", {"consistency": 0.70}),
            "substrate": context.get("substrate", {"S_EM": 0.78}),
            "ethos_hint": context.get("ethos_hint", {}),
            "t": context.get("t", now % 1.0),
        }
        signals = self._sym.evaluate(merged)
        self._last_signals = signals
        self._last_context = merged
        ethos_min = min(signals.ethos.values()) if signals.ethos else 0.0
        snapshot = MasterStateSnapshot(
            coherence=signals.coherence,
            impetus=signals.impetus,
            risk=signals.risk,
            uncertainty=signals.uncertainty,
            mirror_consistency=signals.mirror_consistency,
            substrate_readiness=signals.S_EM,
            ethos_min=ethos_min,
            embodiment_phase=float(signals.embodiment.get("phase", 0.0)),
            timestamp=now,
            explain=signals.explain,
        )
        return snapshot

    def last_snapshot(self) -> Optional[MasterStateSnapshot]:
        if not self._last_signals:
            return None
        ethos_min = (
            min(self._last_signals.ethos.values()) if self._last_signals.ethos else 0.0
        )
        return MasterStateSnapshot(
            coherence=self._last_signals.coherence,
            impetus=self._last_signals.impetus,
            risk=self._last_signals.risk,
            uncertainty=self._last_signals.uncertainty,
            mirror_consistency=self._last_signals.mirror_consistency,
            substrate_readiness=self._last_signals.S_EM,
            ethos_min=ethos_min,
            embodiment_phase=float(self._last_signals.embodiment.get("phase", 0.0)),
            timestamp=time.time(),
            explain=self._last_signals.explain,
        )


_MASTER_SYMBOLIC_SINGLETON: Optional[MasterSymbolicEquation] = None


def get_master_symbolic_singleton() -> MasterSymbolicEquation:
    global _MASTER_SYMBOLIC_SINGLETON
    if _MASTER_SYMBOLIC_SINGLETON is None:
        _MASTER_SYMBOLIC_SINGLETON = MasterSymbolicEquation()
    return _MASTER_SYMBOLIC_SINGLETON


def evaluate_master_state(
    context: Optional[Dict[str, Any]] = None
) -> MasterStateSnapshot:
    return get_master_symbolic_singleton().evaluate(context)
