from __future__ import annotations

import json
import os
import time
from typing import Any, Dict

from .job_spec import JobSpec

try:  # pragma: no cover - compatibility shim
    from .drivers.null_driver import NullDriver
except Exception:  # pragma: no cover
    from .drivers.driver_null import NullDriver  # type: ignore

from .drivers.k8s_driver import K8sDriver
from .drivers.slurm_driver import SlurmDriver
from .drivers.cloud_driver import CloudDriver

_AUDIT = os.path.join("logs", "cluster_audit.ndjson")
_DRIVERS = {
    "null": NullDriver(),
    "k8s": K8sDriver(),
    "slurm": SlurmDriver(),
    "cloud": CloudDriver(),
}


def _audit(event: str, **payload: Any) -> None:
    try:
        os.makedirs("logs", exist_ok=True)
        with open(_AUDIT, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"ts": time.time(), "event": event, **payload}) + "\n")
    except Exception:  # pragma: no cover - logging must not raise
        pass


def _driver(name: str) -> Any:
    key = (name or "null").lower()
    return _DRIVERS.get(key, _DRIVERS["null"])


def quote_job(spec_dict: Dict[str, Any]) -> Dict[str, Any]:
    spec = JobSpec.from_dict(spec_dict)
    driver = _driver(spec.provider)
    quote = driver.quote(spec.to_dict())
    _audit("cluster_quote", spec=spec.to_dict(), quote=quote)
    return quote


def submit_job(spec_dict: Dict[str, Any]) -> Dict[str, Any]:
    spec = JobSpec.from_dict(spec_dict)
    driver = _driver(spec.provider)
    result = driver.submit(spec.to_dict())
    _audit("cluster_submit", spec=spec.to_dict(), result=result)
    return result


def get_status(provider: str, job_id: str) -> Dict[str, Any]:
    driver = _driver(provider)
    status = driver.status(job_id)
    _audit("cluster_status", provider=provider, job_id=job_id, status=status)
    return status


def cancel_job(provider: str, job_id: str) -> Dict[str, Any]:
    driver = _driver(provider)
    status = driver.cancel(job_id)
    _audit("cluster_cancel", provider=provider, job_id=job_id, status=status)
    return status


__all__ = ["quote_job", "submit_job", "get_status", "cancel_job"]
