from __future__ import annotations
import warnings as _warnings
from importlib import import_module as _imp

if not globals().get("_DASHBOARD_SHIM_WARNED_LOG"):
    _warnings.warn(
        "Deprecated import: 'dashboard.dashboard_logger'. Use 'web_planning.backend.dashboard' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    globals()["_DASHBOARD_SHIM_WARNED_LOG"] = True

try:
    from common.audit_chain import append_event as _audit

    _audit(
        actor="system",
        action="deprecated_import",
        ctx={},
        payload={"module": "dashboard.dashboard_logger"},
    )
except Exception:
    pass

_backend = _imp("web_planning.backend.dashboard")
for _k in dir(_backend):
    if not _k.startswith("_"):
        globals()[_k] = getattr(_backend, _k)
del _backend
