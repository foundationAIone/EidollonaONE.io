"""Quantum Probabilistic Information Rendering (QPIR) bring-up stubs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from ai_core.ai_brain import BrainSnapshot

try:  # optional FastAPI integration
    from fastapi import APIRouter
except Exception:  # pragma: no cover
    APIRouter = None  # type: ignore

from .system import QPIRSystem, RenderConfig, RenderSnapshot

@dataclass
class QPIRSnapshot:
    phase_map: Dict[str, float]
    budgets: Dict[str, float]
    phi_echo: float


def render(snapshot: BrainSnapshot, phases: Iterable[str] = ("alpha", "beta", "gamma")) -> QPIRSnapshot:
    base = snapshot.phi_echo
    phase_map = {phase: round(base * (idx + 1) * 0.1, 4) for idx, phase in enumerate(phases)}
    budgets = {"quantum_ms": round(snapshot.omega * 1000, 2), "power_watts": 60.0}
    return QPIRSnapshot(phase_map=phase_map, budgets=budgets, phi_echo=snapshot.phi_echo)


def fastapi_router(system: Optional[QPIRSystem] = None):
    """Return a FastAPI router exposing the QPIR snapshot endpoint."""
    if APIRouter is None:  # pragma: no cover - optional dependency guard
        raise RuntimeError("FastAPI is not installed")

    qp_system = system or QPIRSystem()
    router = APIRouter(prefix="/api/qpir", tags=["qpir"])

    @router.get("/snapshot")
    def snapshot() -> Dict[str, object]:
        snap = qp_system.render_snapshot()
        return qp_system.to_hud_payload(snap)

    return router


__all__ = [
    "QPIRSystem",
    "RenderConfig",
    "RenderSnapshot",
    "QPIRSnapshot",
    "render",
    "fastapi_router",
]
