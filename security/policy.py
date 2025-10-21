from __future__ import annotations

from typing import Any, Dict

DEFAULT_POLICY: Dict[str, Any] = {
    "tokens": {"allowed": ["dev-token"]},
    "rate_limit": {"per_min_per_token": 120},
    "caps": {"cost_usd_max": 10000, "energy_kwh_max": 50000, "hours_max": 72},
}


def get_policy() -> Dict[str, Any]:
    return DEFAULT_POLICY
