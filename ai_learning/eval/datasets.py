"""Dataset loading helpers for the ai_learning evaluation harness."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List


@dataclass(frozen=True)
class EvalSample:
    """Represents a single evaluation item."""

    identifier: str
    category: str
    prompt: str
    reference_answer: str

    @classmethod
    def from_dict(cls, payload: dict) -> "EvalSample":
        try:
            identifier = payload["id"]
            category = payload.get("category", "uncategorised")
            prompt = payload["prompt"]
            reference_answer = payload["reference_answer"]
        except KeyError as exc:  # pragma: no cover - defensive: dataset validated before
            raise ValueError(f"Missing field in dataset row: {exc}") from exc
        return cls(
            identifier=str(identifier),
            category=str(category),
            prompt=str(prompt),
            reference_answer=str(reference_answer),
        )


def _iter_lines(path: Path) -> Iterator[str]:
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            yield line


def load_dataset(path: Path) -> List[EvalSample]:
    """Load an evaluation dataset from a JSON-lines file."""

    if not path.exists():
        raise FileNotFoundError(f"Dataset path does not exist: {path}")

    samples: List[EvalSample] = []
    for line in _iter_lines(path):
        payload = json.loads(line)
        samples.append(EvalSample.from_dict(payload))
    if not samples:
        raise ValueError(f"Dataset {path} did not contain any rows")
    return samples


def list_available_datasets(base_dir: Path) -> List[Path]:
    """Return all JSONL datasets under the given directory."""

    if not base_dir.exists():
        return []
    return sorted([p for p in base_dir.glob("*.jsonl") if p.is_file()])


__all__ = ["EvalSample", "load_dataset", "list_available_datasets"]
