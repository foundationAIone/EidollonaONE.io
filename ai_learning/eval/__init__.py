"""Evaluation harness and utilities for ai_learning."""

from .datasets import EvalSample, load_dataset
from .metrics import DEFAULT_METRICS, RegisteredMetric
from .baselines import RuleBasedBaselineModel
from .registry import MetricRegistry, ModelRegistry
from .harness import (
    EvaluationConfig,
    EvaluationHarness,
    EvaluationSummary,
    ThresholdConfig,
    run_with_config_path,
)

__all__ = [
    "EvalSample",
    "load_dataset",
    "RegisteredMetric",
    "MetricRegistry",
    "ModelRegistry",
    "RuleBasedBaselineModel",
    "EvaluationConfig",
    "EvaluationHarness",
    "EvaluationSummary",
    "ThresholdConfig",
    "DEFAULT_METRICS",
    "run_with_config_path",
]
