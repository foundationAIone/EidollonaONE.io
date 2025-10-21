from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_learning.eval import EvaluationConfig, EvaluationHarness

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = REPO_ROOT / "ai_learning" / "eval" / "data" / "sample_eval_dataset.jsonl"
THRESHOLDS_PATH = REPO_ROOT / "ai_learning" / "eval" / "config" / "default_thresholds.json"


@pytest.mark.ai_eval
@pytest.mark.parametrize(
    "metrics",
    [["exact_match", "token_f1", "keyword_recall"]],
)
def test_eval_harness_creates_expected_outputs(tmp_path: Path, metrics: list[str]) -> None:
    config = EvaluationConfig(
        dataset_path=DATASET_PATH,
        baseline_model="echo_baseline",
        metrics=metrics,
        thresholds_path=THRESHOLDS_PATH,
        output_dir=tmp_path / "results",
    )

    harness = EvaluationHarness()
    summary = harness.run(config)

    assert summary.passed, "Evaluation harness should pass default baseline"
    assert summary.total_cases == 5
    assert summary.passed_cases == summary.total_cases

    summary_path = config.output_dir / "summary.json"
    ndjson_path = config.output_dir / "case_results.ndjson"
    assert summary_path.exists()
    assert ndjson_path.exists()

    stored_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert stored_summary["passed_cases"] == summary.passed_cases
    assert pytest.approx(stored_summary["pass_rate"], rel=1e-6) == summary.pass_rate

    ndjson_lines = [
        json.loads(line)
        for line in ndjson_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert len(ndjson_lines) == summary.total_cases
    assert all("metrics" in line for line in ndjson_lines)
    assert all(set(line["metrics"]) == set(summary.per_metric) for line in ndjson_lines)
