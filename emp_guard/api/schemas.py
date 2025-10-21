from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class DrillIn(BaseModel):
    site: str = "primary"


class RebindIn(BaseModel):
    targets: List[str] = Field(default_factory=list)


class CapsIn(BaseModel):
    cost_usd_max: Optional[float] = None
    hours_max: Optional[float] = None
    energy_kwh_max: Optional[float] = None
