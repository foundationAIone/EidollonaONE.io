"""Built-in evaluation metrics for ai_learning."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Mapping

from .datasets import EvalSample


Tokeniser = Callable[[str], Iterable[str]]
MetricFn = Callable[[str, str, EvalSample], float]


def _default_tokeniser(text: str) -> Iterable[str]:
    cleaned = re.sub(r"[^a-z0-9]+", " ", text.lower())
    tokens = [token for token in cleaned.split() if token]
    return tokens


@dataclass
class RegisteredMetric:
    """A metric registered with the evaluation harness."""

    name: str
    scoring_fn: MetricFn
    description: str

    def compute(self, reference: str, prediction: str, sample: EvalSample) -> float:
        score = float(self.scoring_fn(reference, prediction, sample))
        if math.isnan(score):
            return 0.0
        return max(0.0, min(1.0, score))


_STOPWORDS = {
    "a",
    "an",
    "the",
    "of",
    "and",
    "to",
    "for",
    "in",
    "is",
    "on",
    "with",
    "by",
    "at",
    "from",
}


def _exact_match(reference: str, prediction: str, _: EvalSample) -> float:
    return 1.0 if reference.strip().lower() == prediction.strip().lower() else 0.0


def _token_f1(reference: str, prediction: str, _: EvalSample) -> float:
    ref_tokens = list(_default_tokeniser(reference))
    pred_tokens = list(_default_tokeniser(prediction))
    if not ref_tokens or not pred_tokens:
        return 0.0
    ref_counts = Counter(ref_tokens)
    pred_counts = Counter(pred_tokens)
    overlap = sum(min(ref_counts[token], pred_counts[token]) for token in ref_counts)
    precision = overlap / len(pred_tokens)
    recall = overlap / len(ref_tokens)
    if precision == 0 and recall == 0:
        return 0.0
    return (2 * precision * recall) / (precision + recall)


def _keyword_recall(reference: str, prediction: str, sample: EvalSample) -> float:
    ref_tokens = {
        token
        for token in _default_tokeniser(reference)
        if token not in _STOPWORDS and not token.isdigit()
    }
    if not ref_tokens:
        return 1.0
    pred_tokens = set(_default_tokeniser(prediction))
    hit_count = len(ref_tokens & pred_tokens)
    return hit_count / len(ref_tokens)


DEFAULT_METRICS: Dict[str, RegisteredMetric] = {
    "exact_match": RegisteredMetric(
        name="exact_match",
        scoring_fn=_exact_match,
        description="Strict equality check ignoring case and surrounding whitespace.",
    ),
    "token_f1": RegisteredMetric(
        name="token_f1",
        scoring_fn=_token_f1,
        description="Token-level F1 score using alphanumeric lower-cased tokens.",
    ),
    "keyword_recall": RegisteredMetric(
        name="keyword_recall",
        scoring_fn=_keyword_recall,
        description="Recall of non-stopword reference keywords present in the prediction.",
    ),
}


def aggregate_metric_scores(per_case_scores: Iterable[Mapping[str, float]]) -> Dict[str, float]:
    totals: Dict[str, float] = {}
    counts: Dict[str, int] = {}
    for metrics in per_case_scores:
        for name, value in metrics.items():
            totals[name] = totals.get(name, 0.0) + float(value)
            counts[name] = counts.get(name, 0) + 1
    return {name: (totals[name] / counts[name]) if counts[name] else 0.0 for name in totals}


__all__ = ["RegisteredMetric", "DEFAULT_METRICS", "aggregate_metric_scores"]
