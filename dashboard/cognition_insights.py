from __future__ import annotations

import os as _os
import warnings as _warnings
import logging as _logging
from importlib import import_module as _imp

# ---------------------------------------------------------------------------
# Behavior controls (configure via environment):
#   DASHBOARD_SHIM_MODE   = "warn" | "error" | "silent"   (default: warn)
#   DASHBOARD_CANON_PATH  = "web_planning.backend.dashboard"
# ---------------------------------------------------------------------------
_SHIM_MODE = (_os.environ.get("DASHBOARD_SHIM_MODE") or "warn").lower().strip()
_CANON_PATH = (
    _os.environ.get("DASHBOARD_CANON_PATH") or "web_planning.backend.dashboard"
)

_log = _logging.getLogger("dashboard.cognition_insights.shim")


def _emit_warning_once(message: str) -> None:
    key = "_DASHBOARD_SHIM_WARNED_COG"
    if not globals().get(key):
        if _SHIM_MODE == "warn":
            _warnings.warn(message, DeprecationWarning, stacklevel=2)
        elif _SHIM_MODE == "error":
            raise ImportError(
                f"{message} (shim in ERROR mode via DASHBOARD_SHIM_MODE=error)"
            )
        # silent => no warning
        globals()[key] = True


_MSG = (
    "Deprecated import: 'dashboard.cognition_insights'. "
    "Use 'web_planning.backend.dashboard' instead. "
    f"(Canonical path = '{_CANON_PATH}')"
)
_emit_warning_once(_MSG)

# ---------------------------------------------------------------------------
# Best-effort audit hook (non-blocking)
# ---------------------------------------------------------------------------


def _audit_deprecated_import() -> None:
    try:
        from common.audit_chain import append_event as _append_event  # type: ignore

        _append_event(
            {
                "actor": "system",
                "action": "deprecated_import",
                "context": {
                    "module": "dashboard.cognition_insights",
                    "shim_mode": _SHIM_MODE,
                },
                "payload_digest": "dashboard.cognition_insights",
            }
        )
    except Exception as e:
        _log.debug("cognition_insights shim audit skipped: %s", e)


_audit_deprecated_import()

# ---------------------------------------------------------------------------
# Re-export the canonical API
# ---------------------------------------------------------------------------
try:
    _backend = _imp(_CANON_PATH)
except Exception as e:
    raise ImportError(
        f"Failed to import canonical dashboard module '{_CANON_PATH}'. "
        "Ensure the web_planning backend is in PYTHONPATH and that "
        "web_planning/backend/dashboard/__init__.py is importable. "
        f"Root cause: {e!r}"
    ) from e

__all__ = [name for name in dir(_backend) if not name.startswith("_")]
for _name in __all__:
    globals()[_name] = getattr(_backend, _name)

# Breadcrumb for introspection
__canonical__ = _CANON_PATH

# Clean namespace
del (
    _imp,
    _backend,
    _name,
    _os,
    _warnings,
    _logging,
    _log,
    _MSG,
    _SHIM_MODE,
    _CANON_PATH,
    _audit_deprecated_import,
    _emit_warning_once,
)
