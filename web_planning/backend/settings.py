"""Typed configuration for the SAFE planning backend.

This module centralizes environment-driven flags referenced across
``web_planning.backend``. Historically the FastAPI app accessed a loose
``SAFE_MODE`` global imported from various places; creating a dedicated
settings module gives static analysis tools a concrete source of truth and
eliminates missing-import diagnostics.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    value = value.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


@dataclass(frozen=True)
class BackendSettings:
    """Runtime configuration for the backend service."""

    safe_mode: bool = True

    @property
    def SAFE_MODE(self) -> bool:
        return self.safe_mode

    @classmethod
    def from_env(cls) -> "BackendSettings":
        return cls(
            safe_mode=_parse_bool(
                os.getenv("SAFE_MODE", os.getenv("EIDOLLONA_SAFE_MODE")),
                default=True,
            )
        )


SETTINGS: Final[BackendSettings] = BackendSettings.from_env()

__all__ = ["BackendSettings", "SETTINGS"]

