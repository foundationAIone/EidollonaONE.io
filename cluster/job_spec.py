from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


def _pos(x: float) -> float:
    v = float(x)
    if v < 0:
        raise ValueError("value must be >=0")
    return v


@dataclass
class JobSpec:
    job: str
    provider: str
    resources: Dict[str, float]
    data: Dict[str, Any]
    output: Dict[str, Any]
    caps: Dict[str, float]
    audit: Dict[str, Any]

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "JobSpec":
        required = [
            "job",
            "provider",
            "resources",
            "data",
            "output",
            "caps",
            "audit",
        ]
        for key in required:
            if key not in d:
                raise ValueError(f"missing field: {key}")

        resources = d["resources"]
        caps = d["caps"]
        _pos(resources.get("gpu", 0))
        _pos(resources.get("hours", 0))
        _pos(resources.get("mem_gb", 0))
        if "cost_usd_max" in caps:
            _pos(caps["cost_usd_max"])
        if "energy_kwh_max" in caps:
            _pos(caps["energy_kwh_max"])
        if "hours_max" in caps:
            _pos(caps["hours_max"])

        return JobSpec(
            job=str(d["job"]),
            provider=str(d["provider"]).lower(),
            resources=dict(resources),
            data=dict(d["data"]),
            output=dict(d["output"]),
            caps=dict(caps),
            audit=dict(d["audit"]),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job": self.job,
            "provider": self.provider,
            "resources": self.resources,
            "data": self.data,
            "output": self.output,
            "caps": self.caps,
            "audit": self.audit,
        }


__all__ = ["JobSpec", "_pos"]
