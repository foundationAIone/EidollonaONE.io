from __future__ import annotations

from typing import Any, Dict

from .base import BaseDriver


class SlurmDriver(BaseDriver):
    name = "slurm"

    def quote(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        resources = spec.get("resources", {})
        gpu = float(resources.get("gpu", 0) or 0.0)
        hours = float(resources.get("hours", 0) or 0.0)
        return {
            "eta_hours": hours,
            "cost_usd_est": gpu * hours * 2.8,
            "energy_kwh_est": gpu * hours * 2.1,
            "driver": self.name,
        }

    def submit(self, spec: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover - stub
        return {"job_id": "slurm-UNIMPLEMENTED", "status": "queued"}

    def status(self, job_id: str) -> Dict[str, Any]:  # pragma: no cover - stub
        return {"job_id": job_id, "status": "unknown"}

    def cancel(self, job_id: str) -> Dict[str, Any]:  # pragma: no cover - stub
        return {"job_id": job_id, "status": "cancel_requested"}


__all__ = ["SlurmDriver"]
