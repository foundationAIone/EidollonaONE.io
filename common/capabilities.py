"""
Capability registry (SAFE, static list for local dev/testing).
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional

_CAPS: List[Dict[str, Any]] = [
    {"name": "avatar", "category": "ui", "enabled": True},
    {"name": "speech", "category": "ui", "enabled": True},
    {"name": "planning", "category": "core", "enabled": True},
]


def list_capabilities() -> List[Dict[str, Any]]:
    return list(_CAPS)


def get_capability(name: str) -> Optional[Dict[str, Any]]:
    for c in _CAPS:
        if c.get("name") == name:
            return c
    return None
