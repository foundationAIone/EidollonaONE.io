from __future__ import annotations

from dataclasses import dataclass
import json
import os
import time
import threading
from typing import Any, Callable, Dict, Optional

__all__ = ["audit_ndjson", "AuditSink", "register_sink"]


@dataclass
class AuditSink:
    """Simple callback sink used for testing or custom routing."""

    callback: Callable[[Dict[str, Any]], None]

    def emit(self, record: Dict[str, Any]) -> None:
        try:
            self.callback(record)
        except Exception:
            # Sink failures must never break SAFE workflows
            pass


_sink_lock = threading.Lock()
_custom_sink: Optional[AuditSink] = None
_backfill_done = False


def register_sink(callback: Optional[Callable[[Dict[str, Any]], None]]) -> None:
    """Register (or clear) a custom sink that receives every audit payload."""

    global _custom_sink
    with _sink_lock:
        _custom_sink = AuditSink(callback) if callback is not None else None


def _logs_dir() -> str:
    return os.environ.get("AUDIT_LOG_DIR", "logs")


def _write_file(payload: Dict[str, Any]) -> None:
    base_dir = _logs_dir()
    os.makedirs(base_dir, exist_ok=True)
    path = os.path.join(base_dir, "audit.ndjson")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _ensure_reason_backfill(path: str) -> None:
    global _backfill_done
    if _backfill_done:
        return
    try:
        if not os.path.exists(path):
            _backfill_done = True
            return
        changed = False
        updated: list[str] = []
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.rstrip("\n")
                if not line:
                    updated.append(line)
                    continue
                try:
                    data = json.loads(line)
                except Exception:
                    updated.append(line)
                    continue
                reasons = data.get("reasons")
                if not isinstance(reasons, list) or not reasons:
                    data["reasons"] = ["backfill"]
                    changed = True
                updated.append(json.dumps(data, ensure_ascii=False))
        if changed:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(updated) + "\n")
    except Exception:
        pass
    finally:
        _backfill_done = True


def audit_ndjson(event: str, **payload: Any) -> None:
    """Persist an NDJSON audit entry under `logs/audit.ndjson`."""

    record = {"ts": time.time(), "event": event, **payload}
    reasons = record.get("reasons")
    if not isinstance(reasons, list) or not reasons:
        record["reasons"] = ["unspecified"]
    data_dir = _logs_dir()
    path = os.path.join(data_dir, "audit.ndjson")
    _ensure_reason_backfill(path)
    try:
        _write_file(record)
    except Exception:
        pass

    sink = _custom_sink
    if sink is not None:
        sink.emit(record)
