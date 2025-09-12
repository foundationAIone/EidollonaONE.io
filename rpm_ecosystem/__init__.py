"""Deprecated shim package.

Use `avatar.rpm_ecosystem` instead of `rpm_ecosystem`.
This shim will be removed in a future major version.
"""

from importlib import import_module as _import_module
import warnings as _warnings

_warnings.warn(
    "Importing 'rpm_ecosystem' directly is deprecated; use 'avatar.rpm_ecosystem' instead.",
    DeprecationWarning,
    stacklevel=2,
)

_canonical = _import_module("avatar.rpm_ecosystem")
__all__ = getattr(_canonical, "__all__", [])
for _n in __all__:
    globals()[_n] = getattr(_canonical, _n, None)

del _import_module, _warnings, _canonical, _n
