"""Job queue abstractions for SAFE quantum processing."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, Iterable, Optional
from collections import deque

__all__ = ["QuantumJob", "QuantumJobQueue"]


@dataclass
class QuantumJob:
    """Representation of a quantum computation request."""

    payload: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def summary(self) -> Dict[str, Any]:
        return {
            "keys": sorted(self.payload.keys()),
            "metadata": dict(self.metadata),
        }


class QuantumJobQueue:
    """FIFO queue with deterministic iteration order."""

    def __init__(self) -> None:
        self._queue: Deque[QuantumJob] = deque()
        self._counter = itertools.count()

    def enqueue(self, payload: Dict[str, Any], *, metadata: Optional[Dict[str, Any]] = None) -> QuantumJob:
        job = QuantumJob(payload=dict(payload), metadata=dict(metadata or {}))
        job.metadata.setdefault("job_id", next(self._counter))
        self._queue.append(job)
        return job

    def dequeue(self) -> Optional[QuantumJob]:
        if not self._queue:
            return None
        return self._queue.popleft()

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._queue)

    def peek_all(self) -> Iterable[QuantumJob]:
        return tuple(self._queue)
