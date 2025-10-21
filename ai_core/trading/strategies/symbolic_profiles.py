"""Compatibility shim that re-exports bot symbolic profiles for strategies."""

from ai_core.trading.bots.symbolic_profiles import (  # noqa: F401
    DEFAULT_PROFILE,
    SymbolicProfile,
    build_profile,
)

__all__ = ["SymbolicProfile", "build_profile", "DEFAULT_PROFILE"]
