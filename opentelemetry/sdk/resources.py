"""Resource shim matching minimal OpenTelemetry surface area."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

SERVICE_NAME = "service.name"


@dataclass
class Resource:
    attributes: Dict[str, object]

    @classmethod
    def create(cls, attributes: Dict[str, object]) -> "Resource":
        return cls(attributes=attributes)


__all__ = ["SERVICE_NAME", "Resource"]
