"""master_awaken

Awakening orchestration builds on boot report, performing a few additional
symbolic evaluations and deriving readiness classifications.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
import time
import logging

from .master_boot import boot_system, BootReport
from .symbolic_equation_master import evaluate_master_state, MasterStateSnapshot


@dataclass
class AwakeningReport:
    boot: BootReport
    iterations: int
    final_snapshot: MasterStateSnapshot
    readiness: str
    generated_at: float
    notes: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "boot": self.boot.summary(),
            "iterations": self.iterations,
            "readiness": self.readiness,
            "coherence": round(self.final_snapshot.coherence, 3),
            "impetus": round(self.final_snapshot.impetus, 3),
            "risk": round(self.final_snapshot.risk, 3),
            "uncertainty": round(self.final_snapshot.uncertainty, 3),
            "substrate": round(self.final_snapshot.substrate_readiness, 3),
            "mirror": round(self.final_snapshot.mirror_consistency, 3),
            "ethos_min": round(self.final_snapshot.ethos_min, 3),
            "notes": self.notes,
        }


_LOGGER = logging.getLogger(__name__ + ".awaken")


def _classify(snapshot: MasterStateSnapshot) -> str:
    if snapshot.coherence >= 0.85 and snapshot.impetus >= 0.5:
        return "prime_ready"
    if snapshot.coherence >= 0.75:
        return "ready"
    if snapshot.coherence >= 0.6:
        return "warming"
    return "baseline"


def awaken_consciousness(
    iterations: int = 3, context: Optional[Dict[str, Any]] = None
) -> AwakeningReport:
    boot = boot_system(context)
    snap = boot  # type: ignore[assignment]
    last_snapshot: Optional[MasterStateSnapshot] = None
    # Perform a small number of refinement evaluations (no RNG inside symbolic)
    for i in range(max(1, iterations)):
        last_snapshot = evaluate_master_state(context)
    assert last_snapshot is not None  # for type checker
    readiness = _classify(last_snapshot)
    notes = (
        "stable"
        if readiness in ("prime_ready", "ready")
        else "needs further calibration"
    )
    report = AwakeningReport(
        boot=boot,
        iterations=iterations,
        final_snapshot=last_snapshot,
        readiness=readiness,
        generated_at=time.time(),
        notes=notes,
    )
    _LOGGER.info("Awakening report: %s", report.as_dict())
    return report


__all__ = ["AwakeningReport", "awaken_consciousness"]
