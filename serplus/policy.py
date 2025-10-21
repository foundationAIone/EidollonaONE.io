from __future__ import annotations

from typing import Any, Dict

SER_POLICY: Dict[str, Any] = {
    "ticker": "SER",
    "mint_authority": ["programmerONE"],
    "max_supply": 10_000_000_000.0,
    "decimals": 2,
}

COMP_POLICY: Dict[str, Any] = {
    "ticker": "COMP",
    "decimals": 2,
}


def get_ser_policy() -> Dict[str, Any]:
    """Return a copy of the Serplus policy definition."""

    return dict(SER_POLICY)


def get_comp_policy() -> Dict[str, Any]:
    """Return a copy of the CompCoin policy definition."""

    return dict(COMP_POLICY)
