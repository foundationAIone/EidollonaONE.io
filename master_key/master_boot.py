"""master_boot

Boot sequencing harness. Performs lightweight validation & produces a BootReport
used by higher-level awakening. Side-effects intentionally minimal; no
network / heavy I/O. Designed to run very early.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
import time
import logging

from .symbolic_equation_master import evaluate_master_state, MasterStateSnapshot
from .quantum_master_key import get_master_key, MasterKey


@dataclass
class BootReport:
    ok: bool
    master_key_fingerprint: str
    symbolic_coherence: float
    substrate_readiness: float
    risk: float
    uncertainty: float
    generated_at: float
    details: Dict[str, Any]

    def summary(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "fingerprint": self.master_key_fingerprint[:12],
            "coherence": round(self.symbolic_coherence, 3),
            "substrate": round(self.substrate_readiness, 3),
            "risk": round(self.risk, 3),
            "uncertainty": round(self.uncertainty, 3),
        }


_LOGGER = logging.getLogger(__name__ + ".boot")


def boot_system(context: Optional[Dict[str, Any]] = None) -> BootReport:
    mk: MasterKey = get_master_key()
    snapshot: MasterStateSnapshot = evaluate_master_state(context)
    ok = (
        snapshot.coherence >= 0.6
        and snapshot.substrate_readiness >= 0.6
        and snapshot.risk < 0.6
    )
    report = BootReport(
        ok=ok,
        master_key_fingerprint=mk.fingerprint,
        symbolic_coherence=snapshot.coherence,
        substrate_readiness=snapshot.substrate_readiness,
        risk=snapshot.risk,
        uncertainty=snapshot.uncertainty,
        generated_at=time.time(),
        details={
            "impetus": snapshot.impetus,
            "mirror_consistency": snapshot.mirror_consistency,
            "ethos_min": snapshot.ethos_min,
            "embodiment_phase": snapshot.embodiment_phase,
        },
    )
    level = logging.INFO if report.ok else logging.WARNING
    _LOGGER.log(level, "Boot report: %s", report.summary())
    return report


__all__ = ["BootReport", "boot_system"]
