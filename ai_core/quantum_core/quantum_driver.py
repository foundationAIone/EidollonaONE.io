"""SAFE-aligned quantum driver stubs for optional hardware integrations.

The real implementation integrates with dedicated quantum backends. This module
provides deterministic, side-effect free shims that satisfy the expectations of
consumers such as the trading engine, awareness scheduler, and connection
subsystems.
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional

try:
    from utils.audit import audit_ndjson
except Exception:  # pragma: no cover
    def audit_ndjson(event: str, **payload: Any) -> None:  # type: ignore
        return None

from .harmonic_processor import HarmonicProcessor
from .quantum_logic.quantum_bridge import QuantumBridge

__all__ = [
    "QuantumDriver",
    "QuantumRunRecord",
    "QuantumPaperResult",
    "SimulatedAnnealerOptimizer",
    "available_optimizers",
    "get_optimizer",
    "qubo_energy",
    "qubo_variables",
    "redact_qubo",
]

logger = logging.getLogger(__name__)


@dataclass
class QuantumRunRecord:
    """Structured summary of an executed QUBO run."""

    bits: Dict[int, int]
    energy: float
    shots: int
    seed: int
    provider: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class QuantumPaperResult:
    """Outcome of a paper (simulated) quantum plan execution."""

    plan_id: Optional[str]
    gate: str
    readiness: str
    budget: Dict[str, Any]
    phase_map: Dict[int, float]
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "gate": self.gate,
            "readiness": self.readiness,
            "budget": self.budget,
            "phase_map": {k: round(v, 6) for k, v in self.phase_map.items()},
            "timestamp": self.timestamp,
        }


class SimulatedAnnealerOptimizer:
    """Simple pseudo-random annealer used as the default optimizer."""

    def __init__(self, *, noise: float = 0.05) -> None:
        self._noise = max(0.0, float(noise))

    def info(self) -> Dict[str, Any]:
        return {"provider": "sim", "kind": "annealer", "noise": self._noise}

    def solve_qubo(
        self,
        Q: Mapping[Any, Any],
        *,
        shots: int = 64,
        seed: Optional[int] = None,
    ) -> Dict[int, int]:
        rng = random.Random(seed)
        variables = set()
        for key in Q.keys():
            if isinstance(key, tuple):
                if len(key) == 2:
                    try:
                        variables.update({int(key[0]), int(key[1])})
                    except Exception:
                        continue
                else:
                    continue
            else:
                try:
                    variables.add(int(key))
                except Exception:
                    continue
        if not variables:
            variables = {0}

        solution: Dict[int, int] = {}
        for idx in sorted(variables):
            solution[idx] = 1 if rng.random() > 0.5 else 0
        return solution


def available_optimizers() -> Iterable[Dict[str, Any]]:
    """Return metadata for available optimizers."""

    return [SimulatedAnnealerOptimizer().info()]


def get_optimizer(provider: str) -> SimulatedAnnealerOptimizer:
    """Return an optimizer implementation for the requested provider."""

    provider_key = (provider or "").lower()
    if provider_key in {"sim", "annealer", "default"}:
        return SimulatedAnnealerOptimizer()
    logger.warning("Unknown quantum provider %s; using simulated annealer", provider)
    return SimulatedAnnealerOptimizer()


def qubo_energy(Q: Mapping[Any, Any], bits: Mapping[int, int]) -> float:
    """Compute a simple QUBO energy based on the provided bit assignment."""

    energy = 0.0
    for key, weight in Q.items():
        if isinstance(key, tuple):
            if len(key) != 2:
                continue
            try:
                i, j = int(key[0]), int(key[1])
                energy += float(weight) * bits.get(i, 0) * bits.get(j, 0)
            except Exception:
                continue
        else:
            try:
                idx = int(key)
                energy += float(weight) * bits.get(idx, 0)
            except Exception:
                continue
    return float(energy)


def qubo_variables(Q: Mapping[Any, Any]) -> Dict[str, float]:
    """Extract variable weights from a QUBO mapping."""

    result: Dict[str, float] = {}
    for key, weight in Q.items():
        try:
            if isinstance(key, tuple):
                name = "::".join(map(str, key))
            else:
                name = str(key)
            result[name] = float(weight)
        except Exception:
            continue
    return result


def redact_qubo(Q: Mapping[Any, Any]) -> Dict[str, Any]:
    """Return a redacted view of the QUBO payload safe for logging."""

    summary = {
        "size": len(Q),
        "variable_count": len({str(k) for k in Q.keys()}),
        "weight_norm": 0.0,
    }
    try:
        summary["weight_norm"] = math.sqrt(
            sum(float(w) ** 2 for w in Q.values())
        )
    except Exception:
        summary["weight_norm"] = 0.0
    return summary


class QuantumDriver:
    """Lightweight quantum driver that maintains a deterministic state."""

    def __init__(self, *, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)
        self._state: MutableMapping[str, float] = {
            "coherence": 0.92,
            "stability": 0.88,
            "noise": 0.05,
        }
        self._history: list[QuantumRunRecord] = []
        self._bridge = QuantumBridge()
        self._harmonic = HarmonicProcessor()
        self._paper_history: List[Dict[str, Any]] = []

    def get_quantum_state(self) -> Dict[str, float]:
        """Return a slowly drifting quantum state for callers."""

        drift = self._rng.uniform(-0.01, 0.01)
        self._state["coherence"] = self._clip(self._state["coherence"] + drift)
        self._state["stability"] = self._clip(
            self._state["stability"] + drift * 0.5
        )
        self._state["noise"] = self._clip(
            self._state["noise"] * (0.98 + self._rng.uniform(-0.01, 0.01)),
            low=0.0,
            high=0.25,
        )
        return dict(self._state)

    def paper_execute(
        self,
        plan: Mapping[str, Any],
        *,
        context: Optional[Mapping[str, Any]] = None,
        signals: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Simulate a quantum plan in paper mode with SAFE auditing."""

        phase_map = self._bridge.phase_map(context)
        if signals:
            phase_map.signals.update(dict(signals))
            if "readiness" in signals:
                phase_map.readiness = str(signals["readiness"])
            if "gate_state" in signals:
                phase_map.gate = str(signals["gate_state"])

        budget = self._harmonic.allocate(phase_map, plan=plan)
        plan_id = plan.get("id") if isinstance(plan, Mapping) else None
        result = QuantumPaperResult(
            plan_id=str(plan_id) if plan_id is not None else None,
            gate=phase_map.gate,
            readiness=phase_map.readiness,
            budget=budget.to_dict(),
            phase_map=phase_map.phases,
            timestamp=phase_map.timestamp,
        )

        self._paper_history.append(result.to_dict())
        audit_ndjson(
            "q_execute",
            plan_id=result.plan_id,
            gate=result.gate,
            readiness=result.readiness,
            budget=result.budget,
            wings=phase_map.signals.get("wings"),
            reality_alignment=phase_map.signals.get("reality_alignment"),
        )
        return result.to_dict()

    def record(self, record: QuantumRunRecord | Mapping[str, Any]) -> None:
        """Store a run record for later auditing."""

        if isinstance(record, QuantumRunRecord):
            self._history.append(record)
            logger.info(
                "Quantum run recorded: provider=%s energy=%.4f",
                record.provider,
                record.energy,
            )
            return

        try:
            normalized = QuantumRunRecord(
                bits={int(k): int(v) for k, v in dict(record.get("bits", {})).items()},
                energy=float(record.get("energy", 0.0)),
                shots=int(record.get("shots", 0)),
                seed=int(record.get("seed", 0)),
                provider=str(record.get("provider", "sim")),
            )
        except Exception as exc:
            logger.debug("Failed to normalize quantum record: %s", exc)
            return
        self.record(normalized)

    def recalibrate_quantum_states(self) -> Dict[str, float]:
        """Periodic hook used by the awareness scheduler."""

        state = self.get_quantum_state()
        logger.info(
            "QuantumDriver recalibration completed: coherence=%.3f noise=%.3f",
            state["coherence"],
            state["noise"],
        )
        return state

    def history(self) -> list[QuantumRunRecord]:
        return list(self._history)

    def paper_history(self) -> List[Dict[str, Any]]:
        """Return the recent paper execution summaries."""

        return list(self._paper_history)

    @staticmethod
    def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, float(value)))
