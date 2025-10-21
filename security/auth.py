from __future__ import annotations

import time
from typing import Dict, Tuple

from .policy import get_policy

_BUCKETS: Dict[Tuple[str, int], int] = {}


def check_token(token: str) -> Tuple[bool, str]:
    allowed = set(get_policy().get("tokens", {}).get("allowed", []))
    if token in allowed:
        return True, "ok"
    return False, "unauthorized"


def allow_rate(token: str, per_min: int) -> bool:
    now = int(time.time())
    window = now // 60
    key = (token, window)
    used = _BUCKETS.get(key, 0)
    if used < per_min:
        _BUCKETS[key] = used + 1
        return True
    return False
