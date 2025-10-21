"""Deterministic SAFE-friendly quantum gate definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping, MutableMapping, Sequence

__all__ = ["AVAILABLE_GATES", "QuantumLogicGate", "build_gate_weighting"]


@dataclass(frozen=True)
class QuantumLogicGate:
    """Declarative representation of a quantum-inspired logical gate."""

    name: str
    targets: Sequence[int]
    parameters: Mapping[str, float] = field(default_factory=dict)
    description: str = ""

    def normalized_parameters(self) -> Dict[str, float]:
        """Return parameters clamped to [-1, 1] for deterministic behaviour."""

        result: Dict[str, float] = {}
        for key, value in self.parameters.items():
            try:
                bounded = max(-1.0, min(1.0, float(value)))
            except Exception:
                bounded = 0.0
            result[str(key)] = bounded
        return result

    def weight_contribution(self) -> float:
        """Return a small deterministic contribution derived from parameters."""

        params = self.normalized_parameters()
        if not params:
            return 0.0
        weight = sum((idx + 1) * val for idx, val in enumerate(params.values()))
        return float(weight) / max(1.0, len(self.targets) or 1.0)


AVAILABLE_GATES: Mapping[str, QuantumLogicGate] = {
    "H": QuantumLogicGate(
        name="H",
        targets=(0,),
        description="Hadamard-inspired equal superposition gate",
        parameters={"phase": 0.0},
    ),
    "X": QuantumLogicGate(
        name="X",
        targets=(0,),
        description="Pauli-X style bit flip gate",
        parameters={},
    ),
    "Z": QuantumLogicGate(
        name="Z",
        targets=(0,),
        description="Pauli-Z style phase flip gate",
        parameters={"phase": 0.0},
    ),
    "RX": QuantumLogicGate(
        name="RX",
        targets=(0,),
        description="Rotation about X axis (approximate)",
        parameters={"theta": 0.25},
    ),
    "CX": QuantumLogicGate(
        name="CX",
        targets=(0, 1),
        description="Controlled-X interaction",
        parameters={},
    ),
}


def build_gate_weighting(gates: Iterable[QuantumLogicGate]) -> MutableMapping[str, float]:
    """Aggregate deterministic weights for a sequence of gates."""

    weights: MutableMapping[str, float] = {}
    for gate in gates:
        weights[gate.name] = weights.get(gate.name, 0.0) + gate.weight_contribution()
    return weights
