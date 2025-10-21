from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence

try:
    from arch import arch_model  # type: ignore
except Exception:  # pragma: no cover - dependency optional
    arch_model = None  # type: ignore

try:
    from utils.audit import audit_ndjson as audit
except Exception:  # pragma: no cover - fallback
    def audit(event: str, **payload: Any) -> None:
        return None


@dataclass
class MSGARCHResult:
    sigma: float
    regime_probs: List[float]
    meta: Dict[str, Any]
    stub: bool = False


def _sanitize(series: Iterable[float]) -> List[float]:
    values: List[float] = []
    for value in series:
        try:
            values.append(float(value))
        except Exception:
            continue
    return values


def _softmax(values: Sequence[float]) -> List[float]:
    if not values:
        return []
    m = max(values)
    exps = [math.exp(v - m) for v in values]
    total = sum(exps) or 1.0
    return [v / total for v in exps]


def _stub_result(data: Sequence[float], k: int) -> MSGARCHResult:
    if data:
        mean = sum(abs(x) for x in data) / len(data)
        sigma = math.sqrt(sum((x - mean) ** 2 for x in data) / max(1, len(data) - 1))
    else:
        sigma = 0.0
    probs = [1.0 / max(1, k)] * k
    result = MSGARCHResult(sigma=sigma, regime_probs=probs, meta={"stub": True}, stub=True)
    audit("msgarch_fit", sigma=sigma, stub=True, k=k)
    return result


def fit_ms_garch(returns: Sequence[float], k: int = 2) -> MSGARCHResult:
    data = _sanitize(returns)
    if len(data) < 5 or arch_model is None:
        return _stub_result(data, k)
    try:
        model = arch_model(data, mean="Constant", vol="GARCH", p=1, q=1, dist="normal")
        res = model.fit(update_freq=0, disp="off")
        cond_vol = res.conditional_volatility
        sigma = float(cond_vol[-1]) if len(cond_vol) else 0.0
        residual = res.resid[-1] if len(res.resid) else 0.0
        scale = max(1e-6, sigma)
        scores = []
        for idx in range(k):
            weight = (idx + 1) / (k + 1.0)
            scores.append(weight * abs(residual) / scale)
        probs = _softmax(scores)
        meta = {"a0": float(res.params.get("omega", 0.0)), "a1": float(res.params.get("alpha[1]", 0.0)), "b1": float(res.params.get("beta[1]", 0.0))}
        result = MSGARCHResult(sigma=sigma, regime_probs=probs, meta=meta, stub=False)
        audit("msgarch_fit", sigma=sigma, stub=False, k=k, regime_probs=probs)
        return result
    except Exception:
        return _stub_result(data, k)


def forecast_vol(result: MSGARCHResult, horizon: int = 1) -> float:
    horizon = max(1, int(horizon))
    sigma = max(0.0, float(result.sigma))
    decay = 0.92
    forecast = sigma * math.sqrt(1 + (1 - decay ** horizon))
    audit("msgarch_forecast", sigma=forecast, horizon=horizon, stub=result.stub)
    return forecast


__all__ = ["MSGARCHResult", "fit_ms_garch", "forecast_vol"]
