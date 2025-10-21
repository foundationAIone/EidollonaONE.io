from __future__ import annotations

from typing import Dict

_SWEEPSTAKES_FLAG = False


def enable_sweepstakes(value: bool) -> None:
    global _SWEEPSTAKES_FLAG
    _SWEEPSTAKES_FLAG = bool(value)


def sweepstakes_enabled() -> bool:
    return _SWEEPSTAKES_FLAG


def jurisdiction_ok(user: Dict[str, object]) -> bool:
    # Placeholder gate. Extend with real checks when compliance is ready.
    return False


def official_rules() -> str:
    return "https://fancomp.example.com/rules/sweepstakes"
