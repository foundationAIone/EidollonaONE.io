"""Circuit helpers for SAFE quantum logic simulations."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, Sequence

from .gates import QuantumLogicGate, build_gate_weighting

__all__ = ["GateSequenceResult", "QuantumCircuitModel"]


@dataclass
class GateSequenceResult:
    """Summary of a gate sequence evaluation."""

    weights: Dict[str, float]
    observables: Dict[str, float]
    confidence: float
    notes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QuantumCircuitModel:
    """Lightweight deterministic circuit model used by SAFE simulators."""

    gates: Sequence[QuantumLogicGate]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def gate_count(self) -> int:
        return len(self.gates)

    def compile_summary(self) -> Dict[str, Any]:
        """Return a summary payload suitable for logging/auditing."""

        weights = build_gate_weighting(self.gates)
        return {
            "gate_count": len(self.gates),
            "weights": dict(weights),
            "metadata": dict(self.metadata),
        }

    def simulate(self, state: Mapping[str, float]) -> GateSequenceResult:
        """Produce a deterministic observation based on the provided state."""

        weights = build_gate_weighting(self.gates)
        stability = float(state.get("stability", 0.9))
        coherence = float(state.get("coherence", 0.9))
        noise = float(state.get("noise", 0.05))
        gate_factor = sum(weights.values()) or 1.0

        expectation = max(0.0, min(1.0, coherence * 0.7 + stability * 0.3))
        adjusted = expectation * math.exp(-abs(noise) * gate_factor)
        confidence = max(0.0, min(1.0, adjusted))

        observables = {
            "expected_value": round(adjusted, 6),
            "stability": round(stability, 6),
            "coherence": round(coherence, 6),
            "noise": round(noise, 6),
        }

        notes = {
            "gate_count": len(self.gates),
            "compiled_metadata": dict(self.metadata),
        }

        return GateSequenceResult(weights=dict(weights), observables=observables, confidence=confidence, notes=notes)

    @classmethod
    def from_names(cls, names: Iterable[str]) -> "QuantumCircuitModel":
        gates = [
            QuantumLogicGate(name=name, targets=(idx,))
            for idx, name in enumerate(names)
        ]
        return cls(gates=tuple(gates))
