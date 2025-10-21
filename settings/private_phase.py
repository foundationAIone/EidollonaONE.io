"""Private phase controls toggling immersive or network-heavy features."""

from __future__ import annotations

import os
from typing import Dict

__all__ = ["PRIVATE_PHASE", "SAFE_VR_AR", "phase_status"]

PRIVATE_PHASE: bool = os.getenv("EIDOLLONA_PRIVATE_PHASE", "1") != "0"
SAFE_VR_AR: bool = PRIVATE_PHASE


def phase_status() -> Dict[str, bool]:
    """Return a snapshot describing current private-phase toggles."""

    return {
        "private_phase": PRIVATE_PHASE,
        "safe_vr_ar": SAFE_VR_AR,
    }
