"""Command-line entry point for the ai_learning evaluation harness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ai_learning.eval import EvaluationConfig, EvaluationHarness, EvaluationSummary, run_with_config_path  # noqa: E402

_DEFAULT_CONFIG_PATH = _REPO_ROOT / "ai_learning" / "eval" / "config" / "default_run.json"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the ai_learning evaluation harness.")
    parser.add_argument("--config", type=Path, default=None, help="Path to a JSON evaluation config file.")
    parser.add_argument("--dataset", type=Path, default=None, help="Override dataset path (JSONL).")
    parser.add_argument("--baseline-model", default=None, help="Override the baseline model name to evaluate.")
    parser.add_argument(
        "--metrics",
        nargs="+",
        default=None,
        help="Override the metrics list; defaults to the config file.",
    )
    parser.add_argument("--thresholds", type=Path, default=None, help="Optional thresholds config override (JSON).")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory for results output files.")
    parser.add_argument(
        "--emit-json",
        action="store_true",
        help="Print the full evaluation summary JSON to stdout in addition to the table view.",
    )
    return parser.parse_args()


def _load_config_payload(base_config_path: Path) -> Dict[str, Any]:
    with base_config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _apply_overrides(payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    updated = dict(payload)
    if args.dataset is not None:
        updated["dataset_path"] = str(Path(args.dataset).resolve())
    if args.baseline_model is not None:
        updated["baseline_model"] = args.baseline_model
    if args.metrics is not None:
        updated["metrics"] = list(args.metrics)
    if args.thresholds is not None:
        updated["thresholds_path"] = str(Path(args.thresholds).resolve())
    if args.output_dir is not None:
        updated["output_dir"] = str(Path(args.output_dir).resolve())
    return updated


def _print_summary(summary: EvaluationSummary) -> None:
    status = "PASS" if summary.passed else "FAIL"
    print(f"Status: {status}")
    print(f"Total cases: {summary.total_cases} | Passed: {summary.passed_cases} | Pass rate: {summary.pass_rate:.2f}")
    print("Per-metric scores:")
    for name, value in sorted(summary.per_metric.items()):
        threshold = summary.metric_thresholds.get(name)
        if threshold is None:
            print(f"  - {name}: {value:.2f}")
        else:
            print(f"  - {name}: {value:.2f} (threshold {threshold:.2f})")
    aggregate = summary.aggregate_thresholds
    print(
        "Aggregate thresholds: min pass rate "
        f"{aggregate.get('minimum_pass_rate', 0.0):.2f}, "
        f"min cases passed {int(aggregate.get('minimum_cases_passed', 0))}"
    )


def main() -> int:
    args = _parse_args()
    config_path = args.config or _DEFAULT_CONFIG_PATH
    if not config_path.exists():
        print(f"Configuration file not found: {config_path}", file=sys.stderr)
        return 2

    payload = _load_config_payload(config_path)
    payload = _apply_overrides(payload, args)

    if args.config is None and payload == _load_config_payload(config_path):
        # No overrides requested; fast path uses helper for clarity
        summary = run_with_config_path(config_path)
    else:
        config = EvaluationConfig.from_dict(payload, base_dir=config_path.parent)
        harness = EvaluationHarness()
        summary = harness.run(config)

    _print_summary(summary)
    if args.emit_json:
        print(json.dumps(summary.to_dict(), indent=2))

    return 0 if summary.passed else 1


if __name__ == "__main__":
    sys.exit(main())
