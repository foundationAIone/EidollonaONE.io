"""Deterministic algorithm stubs used for SAFE environments."""

from .safe_amplitude_estimation import SafeAmplitudeEstimator
from .safe_qaoa import SafeQAOAEstimator
from .utils import AlgorithmResult

__all__ = [
    "AlgorithmResult",
    "SafeAmplitudeEstimator",
    "SafeQAOAEstimator",
]
