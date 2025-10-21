"""Legacy trading bots shim.

Historically modules imported ``ai_core.trading_bots`` directly. The canonical
implementations now live under ``ai_core.bots``.  This shim preserves the public
surface so existing integrations keep working while emitting a gentle warning
for migration awareness.
"""

from __future__ import annotations

import warnings

from .. import bots as _bots

# Mirror the canonical exports from ai_core.bots
_SYMBOLS = list(getattr(_bots, "__all__", []))

for name in _SYMBOLS:
    globals()[name] = getattr(_bots, name)

warnings.warn(
    "ai_core.trading_bots is deprecated; import ai_core.bots instead",
    DeprecationWarning,
    stacklevel=2,
)

globals()["__all__"] = _SYMBOLS
