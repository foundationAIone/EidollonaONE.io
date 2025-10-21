from __future__ import annotations

import logging
from threading import RLock
from typing import Any, Dict, Optional

try:
    from consciousness_engine.scheduler import AwarenessScheduler
except Exception:  # pragma: no cover
    AwarenessScheduler = None  # type: ignore


logger = logging.getLogger(__name__)


class SchedulerWorker:
    """Lightweight wrapper to start/stop the awareness scheduler in SAFE mode."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._scheduler: Optional[Any] = None
        self._running: bool = False

    def start(self) -> bool:
        if AwarenessScheduler is None:
            logger.info("AwarenessScheduler unavailable; skipping worker start")
            return False

        with self._lock:
            if self._running:
                return True
            try:
                self._scheduler = AwarenessScheduler()
                self._scheduler.start_scheduling()
                self._running = True
                logger.info("Awareness scheduler started")
                return True
            except Exception as exc:  # pragma: no cover - environment specific
                logger.warning("Failed to start awareness scheduler: %s", exc)
                self._scheduler = None
                self._running = False
                return False

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            try:
                if self._scheduler and hasattr(self._scheduler, "stop_scheduling"):
                    self._scheduler.stop_scheduling()
            except Exception:  # pragma: no cover - defensive
                logger.debug("Scheduler stop raised", exc_info=True)
            finally:
                self._scheduler = None
                self._running = False
                logger.info("Awareness scheduler stopped")

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "has_scheduler": bool(self._scheduler),
                "available": AwarenessScheduler is not None,
            }


_worker: Optional[SchedulerWorker] = None
_worker_lock = RLock()


def get_worker() -> SchedulerWorker:
    global _worker
    with _worker_lock:
        if _worker is None:
            _worker = SchedulerWorker()
        return _worker