from __future__ import annotations
from dataclasses import dataclass


@dataclass
class ModelEvolver:
    steps: int = 0

    def evolve(self) -> None:
        self.steps += 1
