"""Processing monitor for SAFE quantum workloads."""

from __future__ import annotations

from typing import Any, Dict

from .job_queue import QuantumJob

__all__ = ["ProcessingMonitor"]


class ProcessingMonitor:
    """Collect lightweight telemetry about processed jobs."""

    def __init__(self) -> None:
        self.total_submitted = 0
        self.total_completed = 0
        self.last_result: Dict[str, Any] = {}

    def record_submission(self, job: QuantumJob) -> None:
        self.total_submitted += 1
        self.last_result = {"last_submission": job.summary()}

    def record_completion(self, job: QuantumJob, result: Dict[str, Any]) -> None:
        self.total_completed += 1
        self.last_result = {
            "job": job.summary(),
            "result": result,
            "total_submitted": self.total_submitted,
            "total_completed": self.total_completed,
        }

    def summary(self) -> Dict[str, Any]:
        return {
            "total_submitted": self.total_submitted,
            "total_completed": self.total_completed,
            "last_result": dict(self.last_result),
        }
