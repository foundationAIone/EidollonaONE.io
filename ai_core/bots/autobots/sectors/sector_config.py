from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class SectorConfig:
    name: str
    compliance_level: float = 0.7
    data_sensitivity: float = 0.5
    allowed_operations: Dict[str, bool] = field(default_factory=dict)
    policy_hints: Dict[str, Any] = field(default_factory=dict)


def get_default_sector_config(sector: str) -> SectorConfig:
    s = sector.lower()
    if s in ("finance", "treasury", "trading"):
        return SectorConfig(
            name=sector,
            compliance_level=0.85,
            data_sensitivity=0.8,
            allowed_operations={
                "file_operations": True,
                "system_tasks": False,
                "network_ops": True,
                "data_ops": True,
            },
            policy_hints={"audit_required": True, "strict_logging": True},
        )
    if s in ("legal", "governance"):
        return SectorConfig(
            name=sector,
            compliance_level=0.9,
            data_sensitivity=0.9,
            allowed_operations={
                "file_operations": True,
                "system_tasks": False,
                "network_ops": True,
                "data_ops": True,
            },
            policy_hints={"human_review": True},
        )
    if s in ("resilience", "ops", "operations"):
        return SectorConfig(
            name=sector,
            compliance_level=0.8,
            data_sensitivity=0.6,
            allowed_operations={
                "file_operations": True,
                "system_tasks": True,
                "network_ops": True,
                "data_ops": True,
            },
            policy_hints={"redundancy": True, "no_destruction": True},
        )
    if s in ("community", "communications", "social"):
        return SectorConfig(
            name=sector,
            compliance_level=0.75,
            data_sensitivity=0.5,
            allowed_operations={
                "file_operations": True,
                "system_tasks": False,
                "network_ops": True,
                "data_ops": True,
            },
            policy_hints={"human_review": True, "brand_safety": True},
        )
    if s in ("security", "secops"):
        return SectorConfig(
            name=sector,
            compliance_level=0.9,
            data_sensitivity=0.8,
            allowed_operations={
                "file_operations": True,
                "system_tasks": False,
                "network_ops": True,
                "data_ops": True,
            },
            policy_hints={"non_intrusive": True, "scan_only": True},
        )
    if s in ("data", "etl"):
        return SectorConfig(
            name=sector,
            compliance_level=0.8,
            data_sensitivity=0.7,
            allowed_operations={
                "file_operations": True,
                "system_tasks": False,
                "network_ops": True,
                "data_ops": True,
            },
            policy_hints={"schema_validation": True},
        )
    # Default
    return SectorConfig(
        name=sector,
        compliance_level=0.7,
        data_sensitivity=0.5,
        allowed_operations={
            "file_operations": True,
            "system_tasks": True,
            "network_ops": True,
            "data_ops": True,
        },
        policy_hints={},
    )


__all__ = ["SectorConfig", "get_default_sector_config"]
