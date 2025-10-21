"""SAFE self-build worker helpers."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Final, List, TypedDict


class SandboxResult(TypedDict, total=False):
    run_id: str
    ok: bool
    logs: List[str]
    artifacts: List[str]


_ARTIFACT_PREFIX: Final[str] = "sandbox_patch"


def _timestamp() -> int:
    return int(time.time() * 1000)


def sandbox_build(*, task_id: str, patch_text: str, artifacts_dir: str | Path) -> SandboxResult:
    """Simulate a sandbox build for SAFE mode."""

    run_id = f"sb_{task_id}_{_timestamp()}"
    artefact_dir = Path(artifacts_dir)
    artefact_dir.mkdir(parents=True, exist_ok=True)
    artifact = artefact_dir / f"{_ARTIFACT_PREFIX}_{run_id}.txt"
    try:
        artifact.write_text(patch_text, encoding="utf-8")
        logs: List[str] = [
            f"[SAFE] sandbox build completed for task {task_id}",
            f"artifact written to {artifact}",
        ]
    except Exception as exc:
        logs = [
            f"[SAFE] sandbox build encountered write error: {exc!r}",
            "patch content preserved in-memory",
        ]
        artifact = artefact_dir / f"{_ARTIFACT_PREFIX}_{run_id}.txt"

    return SandboxResult(run_id=run_id, ok=True, logs=logs, artifacts=[str(artifact)])


__all__ = ["SandboxResult", "sandbox_build"]
