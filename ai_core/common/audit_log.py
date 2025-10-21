"""Minimal audit log bindings used throughout optional SAFE subsystems."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Mapping

__all__ = ["gate_logger"]

_logger = logging.getLogger("ai_core.audit")


class _AuditLogger:
    """Simple logger-backed writer matching legacy gate logger semantics."""

    __slots__ = ("_logger",)

    def __init__(self) -> None:
        self._logger = _logger

    def write(self, payload: Mapping[str, Any]) -> None:
        try:
            record = dict(payload)
        except Exception:
            record = {"malformed_payload": True, "raw": repr(payload)}
        record.setdefault("timestamp", datetime.utcnow().isoformat())
        try:
            serialized = json.dumps(record, ensure_ascii=False, sort_keys=True)
        except Exception:
            serialized = str(record)
        self._logger.info("gate_event %s", serialized)


_SINGLETON = _AuditLogger()


def gate_logger() -> _AuditLogger:
    """Return a singleton audit logger instance."""

    return _SINGLETON
