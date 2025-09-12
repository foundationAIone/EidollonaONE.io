"""Direct trading bots alias avoiding heavy ai_core top-level imports.

Usage:
    from ai_core.trading_bots_alias import create_crypto_bot

Provides a minimal path that does not trigger quantum_core dependencies.
"""

from .bots import *  # type: ignore

__all__ = [*globals().keys()]
