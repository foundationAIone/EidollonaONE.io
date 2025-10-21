"""SAFE self-build testing utilities.

The production system executes sandboxed test suites. For local SAFE
development we provide a light-weight, typed stub that returns a successful
result while recording the request context for auditability.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final, Iterable

_DEFAULT_LOG_DIR: Final[Path] = Path("web_planning") / "backend" / "state"


def _ensure_log_dir() -> Path:
    _DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    return _DEFAULT_LOG_DIR


def run_tests(
    run_id: str, *, logs: Iterable[str] | None = None
) -> tuple[bool, list[str]]:
    """Simulate a self-build test run."""

    log_dir = _ensure_log_dir()
    log_lines = list(logs) if logs is not None else []
    baseline = f"[SAFE] Self-build tests skipped for run_id={run_id}"
    if baseline not in log_lines:
        log_lines.append(baseline)
    try:
        log_path = log_dir / f"self_build_test_{run_id}.log"
        log_path.write_text("\n".join(log_lines), encoding="utf-8")
    except Exception:
        pass
    return True, log_lines


__all__ = ["run_tests"]
