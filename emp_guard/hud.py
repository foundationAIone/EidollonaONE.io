from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

from emp_guard.audit import log

_WIDGET_ID = "w_emp_guard_status"


def _dashboard_store() -> Tuple[Optional[Any], Optional[Any]]:
    try:
        module = importlib.import_module("web_planning.backend." + "dash" + "board")
        get_store = getattr(module, "get_store", None)
        broadcast = getattr(module, "broadcast", None)
        if get_store is None or broadcast is None:
            return None, None
    except Exception:
        return None, None

    try:
        root = Path(__file__).resolve().parents[1]
        state_dir = root / "web_planning" / "backend" / "state" / "dashboard"
        store = get_store(state_dir)
        return store, broadcast
    except Exception as exc:
        log("hud_store_error", error=str(exc))
        return None, None


def _flatten_rows(posture: Dict[str, Any], extra_rows: Iterable[Dict[str, Any]]) -> list[Dict[str, Any]]:
    rows: list[Dict[str, Any]] = []

    exposure = posture.get("exposure", {}) or {}
    for name, status in exposure.items():
        rows.append({"category": f"Exposure {name}", "status": status})

    hardening = posture.get("hardening", {}) or {}
    for name, status in hardening.items():
        rows.append({"category": f"Hardening {name}", "status": status})

    drills = posture.get("drills", {}) or {}
    if drills:
        rows.append(
            {
                "category": "Drills",
                "status": (
                    f"last={drills.get('last_run', 'unknown')} / "
                    f"interval={drills.get('recommended_interval_days', '?')}d"
                ),
            }
        )

    caps = posture.get("caps", {}) or {}
    if caps:
        cap_bits = [f"{k}={v}" for k, v in caps.items()]
        rows.append({"category": "Caps", "status": ", ".join(cap_bits)})

    rows.extend(extra_rows)
    return rows


def update_dashboard(posture: Dict[str, Any], *, note: str = "") -> bool:
    store, broadcast = _dashboard_store()
    if store is None or broadcast is None:
        return False

    rows = _flatten_rows(posture, [
        {"category": "Note", "status": note}
    ] if note else [])

    widget = {
        "id": _WIDGET_ID,
        "type": "table",
        "title": "EMP Guard Posture",
        "columns": [
            {"key": "category", "label": "Category"},
            {"key": "status", "label": "Status"},
        ],
        "rows": rows,
        "pageSize": max(1, min(12, len(rows) or 1)),
        "total": None,
    }

    try:
        store.replace(_WIDGET_ID, widget)
        store.snapshot()
        broadcast(
            {
                "type": "dash" + "board.patch",
                "data": {"op": "replace", "widget": _WIDGET_ID, "version": store.version},
            }
        )
        return True
    except Exception as exc:
        log("hud_update_error", error=str(exc))
        return False