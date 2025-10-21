from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional

try:
    from utils.audit import audit_ndjson as audit
except Exception:  # pragma: no cover - dev fallback
    def audit(event: str, **payload):  # type: ignore
        return None


_DEFAULT_BUCKET = "default"


def _bucket_key(features: Dict[str, Any]) -> str:
    side = features.get("side", "buy")
    venue = features.get("venue", "unknown")
    urgency = float(features.get("urgency", 0.5))
    bucket = f"{side}:{venue}:{int(urgency * 10)}"
    return bucket


def fit_slippage(feature_rows: Iterable[Dict[str, Any]], fills: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Fit a simple bucketed slippage model from fills."""
    buckets: Dict[str, List[float]] = defaultdict(list)
    for feat, fill in zip(feature_rows, fills):
        bps = float(fill.get("slippage_bps", 0.0))
        key = _bucket_key(feat)
        buckets[key].append(bps)
    model: Dict[str, Dict[str, float]] = {}
    for key, values in buckets.items():
        if not values:
            continue
        avg = sum(values) / float(len(values))
        vol = sum((v - avg) ** 2 for v in values) / max(1.0, float(len(values)))
        model[key] = {"mean_bps": avg, "var_bps": vol}
    if _DEFAULT_BUCKET not in model:
        model[_DEFAULT_BUCKET] = {"mean_bps": 0.0, "var_bps": 0.0}
    audit("slippage_model_fit", buckets=len(model))
    return {"buckets": model}


def predict_slippage(order_ctx: Dict[str, Any], model: Optional[Dict[str, Any]]) -> float:
    if not model:
        return 0.0
    buckets = model.get("buckets") or {}
    key = _bucket_key(order_ctx)
    stats = buckets.get(key) or buckets.get(_DEFAULT_BUCKET)
    if not stats:
        return 0.0
    mean_bps = float(stats.get("mean_bps", 0.0))
    audit("slippage_model_predict", bucket=key, bps=mean_bps)
    return mean_bps


__all__ = ["fit_slippage", "predict_slippage"]
