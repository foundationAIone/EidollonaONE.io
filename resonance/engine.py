from __future__ import annotations

from typing import Any, Dict, List

TONE_TABLE: List[float] = [
    196.0,
    220.0,
    246.9,
    261.6,
    293.7,
    329.6,
    392.0,
    440.0,
    493.9,
    523.3,
    587.3,
    659.3,
]


def twelve_strands(sig: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map SE41 to a 12-tone set (symbolic activation).
    Returns tone frequencies and a suggested cadence_ms.
    """
    coherence = float(sig.get("coherence", 0.0))
    risk = float(sig.get("risk", 1.0))
    base = 440.0 if coherence >= 0.75 and risk <= 0.2 else 261.6
    tones = [round(base * (tone / 440.0), 1) for tone in TONE_TABLE]
    cadence = 600 if coherence >= 0.75 else 900
    return {"tones": tones, "cadence_ms": cadence}
