"""
Logging helpers that respect private-phase banner muting.
"""

from __future__ import annotations

import logging
from .private_phase import MUTE_BANNERS


def quiet_info(logger: logging.Logger, message: str) -> None:
    """Log info if banners are not muted; otherwise debug to keep noise low."""
    if MUTE_BANNERS:
        logger.debug(message)
    else:
        logger.info(message)


def quiet_print(message: str) -> None:
    """Fallback print that respects banner muting."""
    if not MUTE_BANNERS:
        print(message)
