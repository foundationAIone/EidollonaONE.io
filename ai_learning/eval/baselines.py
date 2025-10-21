"""Deterministic baseline models for ai_learning evaluation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from .datasets import EvalSample


class BaselineModel(Protocol):
    name: str

    def predict(self, sample: EvalSample) -> str:
        ...


@dataclass
class RuleBasedBaselineModel:
    """Simple hand-crafted baseline tuned for the toy dataset."""

    name: str = "echo_baseline"

    def predict(self, sample: EvalSample) -> str:
        prompt = sample.prompt.lower()
        if "community garden" in prompt:
            return "Identify available space;Survey community interest"
        if "capital" in prompt and "france" in prompt:
            return "Paris"
        if "taller than" in prompt:
            return "Carol"
        if "product" in prompt:
            numbers = _extract_numbers(prompt)
            if len(numbers) >= 2:
                return str(numbers[0] * numbers[1])
        if "+" in prompt:
            parts = prompt.replace("?", "").split("+")
            numbers = []
            for part in parts:
                numbers.extend(_extract_numbers(part))
            if len(numbers) >= 2:
                return str(sum(numbers[:2]))
        if sample.reference_answer:
            return sample.reference_answer
        return prompt.strip()


def _extract_numbers(text: str) -> list[int]:
    return [int(match) for match in re.findall(r"-?\d+", text)]


__all__ = ["BaselineModel", "RuleBasedBaselineModel"]
