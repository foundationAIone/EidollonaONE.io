from __future__ import annotations

"""
Canonical Dashboard package.

Exports:
	- router: FastAPI router mounted at /dashboard (spec/state/push)
	- get_store: access the singleton DashboardStore (lazy-init)
	- set_broadcaster: register a WS push function
	- broadcast: send dashboard patches to subscribers
	- MAX_WIDGETS: UI/state cap for widgets
	- __version__: dashboard module version (bump on schema/behavior changes)

This package is the single source of truth for dashboard APIs.
Legacy imports under the repo-root 'dashboard.*' are deprecated and shimmed
to forward here with a DeprecationWarning and an audit event.
"""

from .router import router
from .service import (
    get_store,
    set_broadcaster,
    broadcast,
    MAX_WIDGETS,
)

# Semantic version for the dashboard backend surface (router/service).
# Bump on backward-incompatible changes to /dashboard/* or service behaviors.
__version__ = "1.1.0"

__all__ = [
    "router",
    "get_store",
    "set_broadcaster",
    "broadcast",
    "MAX_WIDGETS",
    "__version__",
]
