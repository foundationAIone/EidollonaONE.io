from __future__ import annotations
from dataclasses import dataclass


@dataclass
class SelfCoder:
    commits: int = 0

    def write(self, desc: str) -> str:
        self.commits += 1
        return f"wrote:{self.commits}"


self_coder = SelfCoder()
