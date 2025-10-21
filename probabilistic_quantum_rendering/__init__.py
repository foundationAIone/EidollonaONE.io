"""Probabilistic quantum rendering bring-up surfaces."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ai_core.ai_brain import BrainSnapshot
from quantum_probabilistic_information_rendering_system import render

@dataclass
class RenderingEnvelope:
    readiness: str
    wings_signal: float
    phi_echo: float
    phase_map: Dict[str, float]


def make_envelope(snapshot: BrainSnapshot) -> RenderingEnvelope:
    qpir_snapshot = render(snapshot)
    return RenderingEnvelope(
        readiness=snapshot.readiness,
        wings_signal=snapshot.wings,
        phi_echo=qpir_snapshot.phi_echo,
        phase_map=qpir_snapshot.phase_map
    )
