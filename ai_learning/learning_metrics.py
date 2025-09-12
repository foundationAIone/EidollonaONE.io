from __future__ import annotations
from dataclasses import dataclass
from typing import Dict


@dataclass
class LearningMetrics:
    samples: int = 0

    def record(self, n: int = 1) -> None:
        self.samples += int(n)

    def snapshot(self) -> Dict[str, int]:
        return {"samples": self.samples}


learning_metrics = LearningMetrics()
