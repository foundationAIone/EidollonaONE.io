from __future__ import annotations

from typing import Any, Dict

from .job_spec import JobSpec


def minimal_null_job(job: str, gpu: float = 1.0, hours: float = 0.5) -> Dict[str, Any]:
    spec = JobSpec(
        job=job,
        provider="null",
        resources={"gpu": gpu, "hours": hours, "mem_gb": 8.0},
        data={},
        output={},
        caps={"cost_usd_max": gpu * hours * 5.0},
        audit={"operator": "preset", "gate": "ALLOW"},
    )
    return spec.to_dict()


__all__ = ["minimal_null_job"]
