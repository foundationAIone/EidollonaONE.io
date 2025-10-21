"""SAFE amplitude estimation compatible with Qiskit's API surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from .utils import AlgorithmResult, clamp_probability

__all__ = ["SafeAmplitudeEstimator"]


@dataclass
class EstimationParameters:
    shots: int = 1024
    confidence: float = 0.95


class SafeAmplitudeEstimator:
    """Deterministic amplitude estimator with a Qiskit-inspired interface."""

    def __init__(self, *, shots: int = 1024, confidence: float = 0.95) -> None:
        self.params = EstimationParameters(shots=max(16, shots), confidence=max(0.5, min(0.999, confidence)))

    def estimate(self, amplitude: float, *, metadata: Optional[Mapping[str, Any]] = None) -> AlgorithmResult:
        normalized = clamp_probability(amplitude)
        variance = normalized * (1.0 - normalized) / max(1.0, self.params.shots)
        error_margin = variance ** 0.5
        confidence = min(1.0, max(0.0, self.params.confidence))

        data: Dict[str, Any] = {
            "amplitude": normalized,
            "variance": variance,
            "confidence": confidence,
            "shots": self.params.shots,
        }
        if metadata:
            data.update({f"meta_{k}": v for k, v in metadata.items()})
        return AlgorithmResult(value=normalized, metadata=data, error=error_margin)
