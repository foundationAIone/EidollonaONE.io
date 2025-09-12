# -*- coding: utf-8 -*-
"""
Broadcast History Manager
- Append-only, transparent recordkeeping of planned/simulated events.
- ASCII-safe JSON logging for cross-platform consoles.
"""
from __future__ import annotations
from typing import Dict, Any, List
import json
import os
import time

try:
    # Optional: audit chain integration (safe to skip if unavailable)
    from common.audit_chain import append_event as audit_append
except Exception:
    audit_append = None

_LOG_PATH = os.path.join(os.path.dirname(__file__), "broadcast_log.json")
_ROTATE_MAX = 1000  # rotate when exceeding this many events


def read_history() -> List[Dict[str, Any]]:
    try:
        with open(_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception:
        return []


def append_event(event: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
    data = read_history()
    data.append(event)
    # Audit a minimal digest (no sensitive payloads)
    try:
        if audit_append:
            ch = str(event.get("channel", "")) if isinstance(event, dict) else ""
            bid = str(event.get("id") or event.get("broadcast_id") or "")
            audit_append(
                actor="broadcaster",
                action="broadcast.send",
                ctx={"channel": ch},
                payload={"broadcast_id": bid, "channel": ch},
            )
    except Exception:
        pass
    # Rotate if too large to keep files manageable
    if len(data) > _ROTATE_MAX:
        ts = time.strftime("%Y%m%d%H%M%S")
        rotate_path = os.path.join(
            os.path.dirname(_LOG_PATH), f"broadcast_log.{ts}.json"
        )
        try:
            with open(rotate_path, "w", encoding="utf-8") as rf:
                json.dump(data, rf, ensure_ascii=True, indent=2)
            data = []  # reset current log after rotation
        except Exception:
            # If rotation fails, keep writing to main log without data loss
            pass
    with open(_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=True, indent=2)
