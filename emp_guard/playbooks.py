from __future__ import annotations

from typing import Any, Dict, List

from .audit import log

__all__ = [
    "drill_plan",
    "run_drill",
    "ethos_rebind",
]


def drill_plan(site: str = "primary") -> Dict[str, Any]:
    steps = [
        "announce_drill",
        "backup_snapshot",
        "simulate_anomaly",
        "verify_gate",
        "apply_quarantine_flags",
        "ethos_rebind",
        "debrief",
    ]
    return {"site": site, "steps": steps}


def run_drill(site: str = "primary") -> Dict[str, Any]:
    plan = drill_plan(site)
    log("drill_start", site=site, plan=plan)
    result = {
        "ok": True,
        "site": site,
        "duration_min": 6,
        "notes": "paper drill complete",
    }
    log("drill_done", **result)
    return result


def ethos_rebind(targets: List[str]) -> Dict[str, Any]:
    log("rebind_start", targets=targets)
    result = {
        "ok": True,
        "rebuilt": targets,
        "policy": "Ethos/SE41:compat",
    }
    log("rebind_done", **result)
    return result
