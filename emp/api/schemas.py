from __future__ import annotations

from typing import Dict

from pydantic import BaseModel


class GridIn(BaseModel):
    nx: int = 32
    ny: int = 32
    t: float = 0.0


class StateIn(BaseModel):
    state: Dict[str, object]


class SwarmIn(BaseModel):
    n: int = 32
    seed: int = 7
