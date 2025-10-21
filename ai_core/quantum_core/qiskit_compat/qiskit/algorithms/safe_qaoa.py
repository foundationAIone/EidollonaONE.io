"""SAFE approximation of a QAOA-style optimizer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from .utils import AlgorithmResult, normalize_histogram

__all__ = ["SafeQAOAEstimator"]


@dataclass
class QAOAParameters:
    steps: int = 1
    gamma: float = 0.8
    beta: float = 0.3


class SafeQAOAEstimator:
    """Evaluate a quadratic model using deterministic energy heuristics."""

    def __init__(self, *, steps: int = 1, gamma: float = 0.8, beta: float = 0.3) -> None:
        self.params = QAOAParameters(steps=max(1, steps), gamma=float(gamma), beta=float(beta))

    def evaluate(
        self,
        qubo: Mapping[Tuple[int, int], float],
        *,
        initial_bitstring: Optional[Sequence[int]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> AlgorithmResult:
        bits = list(initial_bitstring or [])
        if not bits:
            variables = sorted({idx for key in qubo.keys() for idx in key})
            bits = [0 for _ in variables]

        energy = 0.0
        for (i, j), weight in qubo.items():
            bit_i = bits[i] if i < len(bits) else 0
            bit_j = bits[j] if j < len(bits) else 0
            if i == j:
                energy += weight * bit_i
            else:
                energy += weight * bit_i * bit_j

        histogram = {"0" * len(bits): max(0.0, 1.0 - abs(energy) * 0.1)}
        histogram.update({"1" * len(bits): min(1.0, abs(energy) * 0.1)})
        distribution = normalize_histogram(histogram)

        metadata_payload: Dict[str, Any] = {
            "steps": self.params.steps,
            "gamma": self.params.gamma,
            "beta": self.params.beta,
            "energy": energy,
            "bitstring_length": len(bits),
            "distribution": distribution,
        }
        if metadata:
            metadata_payload.update({f"meta_{k}": v for k, v in metadata.items()})

        return AlgorithmResult(value=energy, metadata=metadata_payload, error=abs(energy) * 0.05)
