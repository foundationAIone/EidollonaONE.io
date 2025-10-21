"""Symbolic web uplink shim for offline SAFE environments."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Mapping, Optional

__all__ = ["SymbolicWebUplink"]

logger = logging.getLogger(__name__)


class SymbolicWebUplink:
    """Minimal uplink that records symbolic payloads for diagnostics."""

    def __init__(self) -> None:
        self._online = True
        self._history: list[Dict[str, Any]] = []

    def publish(self, channel: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        event = {
            "channel": str(channel),
            "payload": dict(payload),
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._history.append(event)
        try:
            serialized = json.dumps(event, ensure_ascii=False, sort_keys=True)
        except Exception:
            serialized = str(event)
        logger.info("Symbolic uplink publish: %s", serialized)
        return event

    def last_event(self) -> Optional[Dict[str, Any]]:
        return self._history[-1] if self._history else None

    def status(self) -> Dict[str, Any]:
        return {
            "online": self._online,
            "events": len(self._history),
            "last_event": self.last_event(),
        }

    def go_offline(self) -> None:
        self._online = False
        logger.warning("SymbolicWebUplink marked offline")

    def go_online(self) -> None:
        self._online = True
        logger.info("SymbolicWebUplink marked online")
