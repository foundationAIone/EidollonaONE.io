from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Dict

from .base import BaseDriver

_STORE = os.path.join("logs", "cluster_null_jobs.json")


def _load() -> Dict[str, Any]:
    os.makedirs("logs", exist_ok=True)
    if not os.path.exists(_STORE):
        return {"jobs": {}}
    try:
        with open(_STORE, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {"jobs": {}}


def _save(db: Dict[str, Any]) -> None:
    with open(_STORE, "w", encoding="utf-8") as handle:
        json.dump(db, handle, ensure_ascii=False, indent=2)


class NullDriver(BaseDriver):
    name = "null"

    def quote(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        resources = spec.get("resources", {})
        gpu = float(resources.get("gpu", 0) or 0.0)
        hours = float(resources.get("hours", 0) or 0.0)
        return {
            "eta_hours": hours,
            "cost_usd_est": round(gpu * hours * 2.5, 2),
            "energy_kwh_est": round(gpu * hours * 2.0, 2),
            "driver": self.name,
        }

    def submit(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        db = _load()
        job_id = "null-" + uuid.uuid4().hex[:12]
        now = time.time()
        db["jobs"][job_id] = {
            "spec": spec,
            "status": "running",
            "submitted_ts": now,
            "updated_ts": now,
            "progress": 0.0,
        }
        _save(db)
        return {"job_id": job_id, "status": "running"}

    def status(self, job_id: str) -> Dict[str, Any]:
        db = _load()
        job = db["jobs"].get(job_id)
        if not job:
            return {"job_id": job_id, "status": "not_found"}
        elapsed = time.time() - job["submitted_ts"]
        if elapsed > 4.0:
            job["status"] = "succeeded"
            job["progress"] = 1.0
        else:
            job["progress"] = min(1.0, elapsed / 4.0)
        job["updated_ts"] = time.time()
        db["jobs"][job_id] = job
        _save(db)
        artifacts = []

        if job["status"] == "succeeded":
            artifacts = [
                {"path": "s3://simulated/artifacts/outputs.json"},
            ]
        return {
            "job_id": job_id,
            "status": job["status"],
            "progress": round(job["progress"], 3),
            "artifacts": artifacts,
        }

    def cancel(self, job_id: str) -> Dict[str, Any]:
        db = _load()
        job = db["jobs"].get(job_id)
        if not job:
            return {"job_id": job_id, "status": "not_found"}
        if job["status"] in ("succeeded", "failed", "canceled"):
            return {"job_id": job_id, "status": job["status"]}
        job["status"] = "canceled"
        job["updated_ts"] = time.time()
        db["jobs"][job_id] = job
        _save(db)
        return {"job_id": job_id, "status": "canceled"}


__all__ = ["NullDriver"]
