"""Evaluation harness for ai_learning models."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional

from .datasets import EvalSample, load_dataset
from .metrics import RegisteredMetric, aggregate_metric_scores
from .registry import MetricRegistry, ModelRegistry, build_default_registries


_MODULE_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class ThresholdConfig:
    """Threshold configuration for evaluation runs."""

    metric_targets: Dict[str, float] = field(default_factory=dict)
    minimum_pass_rate: float = 0.0
    minimum_cases_passed: int = 0

    @classmethod
    def load(cls, path: Optional[Path]) -> "ThresholdConfig":
        if path and path.exists():
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            metric_targets = {
                key: float(value) for key, value in payload.get("metric_targets", {}).items()
            }
            aggregate = payload.get("aggregate", {})
            return cls(
                metric_targets=metric_targets,
                minimum_pass_rate=float(aggregate.get("minimum_pass_rate", 0.0)),
                minimum_cases_passed=int(aggregate.get("minimum_cases_passed", 0)),
            )
        return cls()

    def metric_pass(self, name: str, score: float) -> bool:
        target = self.metric_targets.get(name)
        if target is None:
            return True
        return score >= target


@dataclass
class EvaluationConfig:
    dataset_path: Path
    baseline_model: str
    metrics: List[str]
    thresholds_path: Optional[Path] = None
    output_dir: Path = Path("outputs/ai_learning_eval")

    @classmethod
    def from_dict(cls, payload: Mapping[str, object], base_dir: Optional[Path] = None) -> "EvaluationConfig":
        base = Path(base_dir) if base_dir else Path.cwd()
        dataset_raw = str(payload.get("dataset_path", ""))
        if not dataset_raw:
            raise ValueError("dataset_path must be provided in evaluation config")
        dataset = Path(dataset_raw)
        if not dataset.is_absolute():
            dataset = (base / dataset).resolve()
        if not dataset.exists():
            dataset = (_MODULE_ROOT / dataset_raw).resolve()
        thresholds_path = payload.get("thresholds_path")
        threshold_path_resolved = None
        if isinstance(thresholds_path, str):
            threshold_path_resolved = (base / thresholds_path).resolve()
            if not threshold_path_resolved.exists():
                threshold_path_resolved = (_MODULE_ROOT / thresholds_path).resolve()
        raw_metrics = payload.get("metrics")
        if isinstance(raw_metrics, (list, tuple, set)):
            metrics = [str(metric) for metric in raw_metrics]
        elif isinstance(raw_metrics, str):
            metrics = [raw_metrics]
        else:
            metrics = []
        output_dir = payload.get("output_dir")
        if isinstance(output_dir, str):
            output_path = (base / output_dir).resolve()
        else:
            output_path = (base / "outputs/ai_learning_eval").resolve()
        return cls(
            dataset_path=dataset,
            baseline_model=str(payload.get("baseline_model", "echo_baseline")),
            metrics=metrics or ["exact_match", "token_f1"],
            thresholds_path=threshold_path_resolved,
            output_dir=output_path,
        )


@dataclass
class CaseResult:
    sample_id: str
    prediction: str
    metrics: Dict[str, float]
    passed: bool


@dataclass
class EvaluationSummary:
    started_at: float
    completed_at: float
    total_cases: int
    passed_cases: int
    pass_rate: float
    per_metric: Dict[str, float]
    metric_thresholds: Dict[str, float]
    aggregate_thresholds: Dict[str, float]
    cases: List[CaseResult]

    def to_dict(self) -> Dict[str, object]:
        return {
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "pass_rate": self.pass_rate,
            "per_metric": self.per_metric,
            "metric_thresholds": self.metric_thresholds,
            "aggregate_thresholds": self.aggregate_thresholds,
            "cases": [asdict(case) for case in self.cases],
        }

    @property
    def passed(self) -> bool:
        minimum_pass_rate = self.aggregate_thresholds.get("minimum_pass_rate", 0.0)
        minimum_cases = int(self.aggregate_thresholds.get("minimum_cases_passed", 0))
        return self.pass_rate >= minimum_pass_rate and self.passed_cases >= minimum_cases


class EvaluationHarness:
    """Coordinates model evaluation over datasets and metrics."""

    def __init__(
        self,
        metric_registry: Optional[MetricRegistry] = None,
        model_registry: Optional[ModelRegistry] = None,
    ) -> None:
        if metric_registry is None or model_registry is None:
            metric_registry_default, model_registry_default = build_default_registries()
            self.metric_registry = metric_registry or metric_registry_default
            self.model_registry = model_registry or model_registry_default
        else:
            self.metric_registry = metric_registry
            self.model_registry = model_registry

    def run(self, config: EvaluationConfig) -> EvaluationSummary:
        samples: List[EvalSample] = load_dataset(config.dataset_path)
        thresholds = ThresholdConfig.load(config.thresholds_path)
        model = self.model_registry.get(config.baseline_model)

        requested_metrics: List[RegisteredMetric] = [self.metric_registry.get(name) for name in config.metrics]

        results: List[CaseResult] = []
        passed_cases = 0
        started_at = time.time()
        ndjson_lines: List[str] = []

        for sample in samples:
            prediction = model.predict(sample)
            metric_scores = {
                metric.name: metric.compute(sample.reference_answer, prediction, sample)
                for metric in requested_metrics
            }
            case_passed = all(
                thresholds.metric_pass(metric_name, score)
                for metric_name, score in metric_scores.items()
            )
            if case_passed:
                passed_cases += 1
            result = CaseResult(
                sample_id=sample.identifier,
                prediction=prediction,
                metrics=metric_scores,
                passed=case_passed,
            )
            results.append(result)
            ndjson_lines.append(json.dumps({
                "sample_id": result.sample_id,
                "prediction": result.prediction,
                "metrics": result.metrics,
                "passed": result.passed,
            }))

        completed_at = time.time()
        per_metric = aggregate_metric_scores((result.metrics for result in results))
        pass_rate = passed_cases / len(results) if results else 0.0

        summary = EvaluationSummary(
            started_at=started_at,
            completed_at=completed_at,
            total_cases=len(results),
            passed_cases=passed_cases,
            pass_rate=pass_rate,
            per_metric=per_metric,
            metric_thresholds=thresholds.metric_targets,
            aggregate_thresholds={
                "minimum_pass_rate": thresholds.minimum_pass_rate,
                "minimum_cases_passed": thresholds.minimum_cases_passed,
            },
            cases=results,
        )

        self._write_outputs(config.output_dir, summary, ndjson_lines)
        return summary

    def _write_outputs(self, output_dir: Path, summary: EvaluationSummary, ndjson_lines: Iterable[str]) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        ndjson_path = output_dir / "case_results.ndjson"
        summary_path = output_dir / "summary.json"
        with ndjson_path.open("w", encoding="utf-8") as handle:
            for line in ndjson_lines:
                handle.write(line)
                handle.write("\n")
        with summary_path.open("w", encoding="utf-8") as handle:
            json.dump(summary.to_dict(), handle, indent=2)


def run_with_config_path(config_path: Path) -> EvaluationSummary:
    with config_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    config = EvaluationConfig.from_dict(payload, base_dir=config_path.parent)
    harness = EvaluationHarness()
    return harness.run(config)


__all__ = [
    "EvaluationHarness",
    "EvaluationConfig",
    "ThresholdConfig",
    "EvaluationSummary",
    "run_with_config_path",
]
