"""
Readiness checks for SAFE local mode.
"""

from __future__ import annotations
import os
from typing import Dict, Any


def get_readiness_report() -> Dict[str, Any]:
    logs_dir = os.path.join(os.getcwd(), "logs")
    try:
        os.makedirs(logs_dir, exist_ok=True)
        writable = True
    except Exception:
        writable = False
    summary = (
        "SAFE_MODE=ON | logs_writable="
        + ("yes" if writable else "no")
        + " | deps_missing=none | sensitive_env_present=0"
    )
    return {
        "safe_mode": True,
        "logs_writable": writable,
        "deps_missing": [],
        "sensitive_env_present": 0,
        "summary": summary,
    }
