from __future__ import annotations

import os as _os
import warnings as _warnings
import logging as _logging
from importlib import import_module as _imp

# -----------------------------------------------------------------------------
# Behavior controls (set before import to tune the shim):
#   DASHBOARD_SHIM_MODE = "warn" | "error" | "silent"   (default: warn)
#   DASHBOARD_CANON_PATH = "web_planning.backend.dashboard"
# -----------------------------------------------------------------------------
_SHIM_MODE = (_os.environ.get("DASHBOARD_SHIM_MODE") or "warn").lower().strip()
_CANON_PATH = (
    _os.environ.get("DASHBOARD_CANON_PATH") or "web_planning.backend.dashboard"
)

_log = _logging.getLogger("dashboard.shim")


def _emit_warning_once(message: str) -> None:
    key = "_DASHBOARD_SHIM_WARNED"
    if not globals().get(key):
        # Respect mode
        if _SHIM_MODE == "warn":
            _warnings.warn(message, DeprecationWarning, stacklevel=2)
        elif _SHIM_MODE == "error":
            # Raise a clean error that explains how to fix it
            raise ImportError(
                f"{message} (shim running in ERROR mode via DASHBOARD_SHIM_MODE=error)"
            )
        # silent => do nothing
        globals()[key] = True


# Human-friendly message used for both warning and error modes
_MSG = (
    "Deprecated import: 'dashboard'. Use 'web_planning.backend.dashboard' instead. "
    f"(Canonical path = '{_CANON_PATH}')"
)
_emit_warning_once(_MSG)


# -----------------------------------------------------------------------------
# Best-effort audit (never blocks the import path)
# -----------------------------------------------------------------------------
def _audit_deprecated_import() -> None:
    try:
        # Soft import to avoid hard dependency cycles
        from common.audit_chain import append_event as _append_event  # type: ignore

        _append_event(
            actor="system",
            action="deprecated_import",
            ctx={"module": "dashboard", "shim_mode": _SHIM_MODE},
            payload={"module": "dashboard"},
        )
    except Exception as e:
        # Don’t fail imports because audit isn’t available yet
        _log.debug("dashboard shim audit skipped: %s", e)


_audit_deprecated_import()

# -----------------------------------------------------------------------------
# Re-export canonical API
# -----------------------------------------------------------------------------
try:
    _backend = _imp(_CANON_PATH)
except Exception as e:
    # Give a crisp remediation path if the canonical module is missing/broken
    raise ImportError(
        f"Failed to import canonical dashboard module '{_CANON_PATH}'. "
        "Ensure the web_planning backend is in PYTHONPATH and that "
        "web_planning/backend/dashboard/__init__.py is importable. "
        f"Root cause: {e!r}"
    ) from e

# Build __all__ from the canonical module’s public symbols
_exports = tuple(n for n in dir(_backend) if not n.startswith("_"))
__all__ = _exports  # pyright: ignore[reportUnsupportedDunderAll]

# Re-export every public attribute
for _name in __all__:
    globals()[_name] = getattr(_backend, _name)

# Keep a minimal breadcrumb for introspection
__canonical__ = _CANON_PATH

# Clean module namespace
del (
    _imp,
    _backend,
)
