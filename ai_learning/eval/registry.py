"""Registries for metrics and baseline models."""

from __future__ import annotations

from typing import Dict, Iterable

from .baselines import BaselineModel, RuleBasedBaselineModel
from .metrics import DEFAULT_METRICS, RegisteredMetric


class MetricRegistry:
    """Stores available metrics by name."""

    def __init__(self) -> None:
        self._metrics: Dict[str, RegisteredMetric] = {}

    def register(self, metric: RegisteredMetric) -> None:
        self._metrics[metric.name] = metric

    def bulk_register(self, metrics: Iterable[RegisteredMetric]) -> None:
        for metric in metrics:
            self.register(metric)

    def get(self, name: str) -> RegisteredMetric:
        if name not in self._metrics:
            raise KeyError(f"Unknown metric requested: {name}")
        return self._metrics[name]

    def all(self) -> Dict[str, RegisteredMetric]:
        return dict(self._metrics)


class ModelRegistry:
    """Stores baseline models by name."""

    def __init__(self) -> None:
        self._models: Dict[str, BaselineModel] = {}

    def register(self, model: BaselineModel) -> None:
        self._models[model.name] = model

    def get(self, name: str) -> BaselineModel:
        if name not in self._models:
            raise KeyError(f"Unknown baseline model requested: {name}")
        return self._models[name]

    def all(self) -> Dict[str, BaselineModel]:
        return dict(self._models)


def build_default_registries() -> tuple[MetricRegistry, ModelRegistry]:
    metrics = MetricRegistry()
    metrics.bulk_register(DEFAULT_METRICS.values())

    models = ModelRegistry()
    models.register(RuleBasedBaselineModel())
    return metrics, models


__all__ = [
    "MetricRegistry",
    "ModelRegistry",
    "build_default_registries",
]
