"""HUD API endpoints for Safe bring-up."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from ai_core.ai_brain import AIBrain
from probabilistic_quantum_rendering import make_envelope
from quantum_probabilistic_information_rendering_system.system import QPIRSystem

router = APIRouter(prefix="/api/hud", tags=["hud"])
_brain = AIBrain()
_qpir = QPIRSystem()


@router.get("/signals")
def get_signals(time_lens: str | None = None) -> Dict[str, Any]:
    envelope = make_envelope(_brain.snapshot)
    payload: Dict[str, Any] = _brain.hud_payload()

    qpir_payload: Dict[str, Any] | None = None
    try:
        snapshot = _qpir.render_snapshot()
        qpir_payload = _qpir.to_hud_payload(snapshot)
    except Exception:
        qpir_payload = None

    payload.update({
        "phase_map": envelope.phase_map,
        "phi_echo": envelope.phi_echo,
        "qpir": qpir_payload,
    })
    payload["time_lens"] = time_lens or "now"
    return payload
