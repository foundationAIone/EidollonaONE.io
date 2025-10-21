"""Lightweight symbolic envelope parsing helpers.

The production system exposes a richer symbolic control layer used to steer
planning outputs. For local SAFE builds we only need a typed, resilient parser
that can sanitize the optional fields without depending on heavier imports.
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, TypedDict, cast


class SymbolicEnvelope(TypedDict, total=False):
    intent: str
    domain: str
    priority: str
    coherence_bias: float
    perf_mode: str


_ALLOWED_KEYS = {"intent", "domain", "priority", "coherence_bias", "perf_mode"}
_STR_KEYS = {"intent", "domain", "priority", "perf_mode"}
_FLOAT_KEYS = {"coherence_bias"}


def _as_mapping(candidate: Any) -> Mapping[str, Any] | None:
    if isinstance(candidate, Mapping):
        return candidate
    if isinstance(candidate, MutableMapping):
        return candidate
    return None


def _as_clean_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    try:
        cleaned = str(value).strip()
        return cleaned or None
    except Exception:
        return None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_envelope(payload: Mapping[str, Any] | None) -> SymbolicEnvelope:
    """Extract a normalized symbolic envelope from an incoming payload.

    payload is typically the dict produced by ChatInput.dict() but may also
    contain a nested `envelope` member. Only a curated set of keys are
    returned, and values are coerced to their expected primitive types.
    """

    env: SymbolicEnvelope = {}
    if payload is None:
        return env

    candidates: list[Mapping[str, Any]] = [payload]
    nested = payload.get("envelope")
    nested_mapping = _as_mapping(nested)
    if nested_mapping:
        candidates.append(nested_mapping)

    for candidate in candidates:
        for key in _ALLOWED_KEYS:
            if key not in candidate:
                continue
            raw_value = candidate.get(key)
            if key in _STR_KEYS:
                normalized = _as_clean_str(raw_value)
                if normalized is not None:
                    env[key] = normalized
            elif key in _FLOAT_KEYS:
                number = _as_float(raw_value)
                if number is not None:
                    env[key] = number

    return cast(SymbolicEnvelope, env)


__all__ = ["SymbolicEnvelope", "parse_envelope"]
