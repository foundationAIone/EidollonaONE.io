"""Lightweight CI precheck for ai_learning evaluation harness."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ai_learning.eval import run_with_config_path  # noqa: E402

_DEFAULT_CONFIG_PATH = _REPO_ROOT / "ai_learning" / "eval" / "config" / "default_run.json"


def main() -> int:
    summary = run_with_config_path(_DEFAULT_CONFIG_PATH)
    status = "PASS" if summary.passed else "FAIL"
    print(f"[ai_learning] CI precheck status: {status}")
    print(
        f"Cases passed {summary.passed_cases}/{summary.total_cases} | "
        f"pass rate {summary.pass_rate:.2f}"
    )
    for name, score in sorted(summary.per_metric.items()):
        threshold = summary.metric_thresholds.get(name)
        if threshold is None:
            print(f"  metric {name}: {score:.2f}")
        else:
            print(f"  metric {name}: {score:.2f} (threshold {threshold:.2f})")
    if not summary.passed:
        print("Detailed summary:")
        print(json.dumps(summary.to_dict(), indent=2))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
