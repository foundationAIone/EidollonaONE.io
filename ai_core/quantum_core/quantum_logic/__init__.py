"""SAFE-aligned quantum logic helpers.

This package provides lightweight abstractions for composing deterministic gate
sequences, compiling them into annotated payloads, and reconciling the results
with symbolic reasoning components.  The implementations avoid hardware
side-effects and remain fully operational in headless test environments.
"""

from .gates import QuantumLogicGate, AVAILABLE_GATES
from .circuit import QuantumCircuitModel, GateSequenceResult
from .quantum_bridge import QuantumSymbolicBridge, QSimConfig, BridgeReport

__all__ = [
    "AVAILABLE_GATES",
    "GateSequenceResult",
    "QuantumCircuitModel",
    "QuantumLogicGate",
    "QuantumSymbolicBridge",
    "QSimConfig",
    "BridgeReport",
]
