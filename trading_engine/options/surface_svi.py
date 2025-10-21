from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

try:
    from utils.audit import audit_ndjson as audit
except Exception:  # pragma: no cover - fallback
    def audit(event: str, **payload: Any) -> None:
        return None


@dataclass
class SVIParams:
    a: float
    b: float
    rho: float
    m: float
    sigma: float


def _sanitize_quotes(quotes: Iterable[Dict[str, Any]]) -> List[Dict[str, float]]:
    clean: List[Dict[str, float]] = []
    for row in quotes:
        k_val = row.get("k")
        t_val = row.get("t")
        iv_val = row.get("iv")
        if k_val is None or t_val is None or iv_val is None:
            continue
        try:
            k = float(k_val)
            t = float(t_val)
            iv = max(1e-4, float(iv_val))
        except Exception:
            continue
        if not math.isfinite(k) or not math.isfinite(t) or t <= 0:
            continue
        clean.append({"k": k, "t": t, "iv": iv})
    return clean


def _initial_params(quotes: List[Dict[str, float]]) -> SVIParams:
    if not quotes:
        return SVIParams(0.01, 0.1, 0.0, 0.0, 0.1)
    ivs = [q["iv"] for q in quotes]
    return SVIParams(min(ivs), 0.2, 0.0, 0.0, 0.1)


def _svi_total_variance(params: SVIParams, k: float) -> float:
    diff = k - params.m
    return params.a + params.b * (params.rho * diff + math.sqrt(diff * diff + params.sigma * params.sigma))


def _penalty(params: SVIParams) -> float:
    penalty = 0.0
    if params.b <= 0:
        penalty += 1e6
    if abs(params.rho) >= 1:
        penalty += 1e6
    if params.sigma <= 0:
        penalty += 1e6
    return penalty


def fit_svi_arbitrage_free(quotes: Iterable[Dict[str, Any]], max_iter: int = 200) -> SVIParams:
    data = _sanitize_quotes(quotes)
    params = _initial_params(data)
    if not data:
        audit("svi_fit", ok=False, reason="no_data")
        return params
    lr = 0.01
    for _ in range(max_iter):
        grad = {"a": 0.0, "b": 0.0, "rho": 0.0, "m": 0.0, "sigma": 0.0}
        loss = 0.0
        for row in data:
            k = row["k"]
            t = row["t"]
            target_var = row["iv"] ** 2 * t
            model_var = _svi_total_variance(params, k)
            diff = model_var - target_var
            loss += 0.5 * diff * diff
            diff_k = k - params.m
            sqrt_term = math.sqrt(diff_k * diff_k + params.sigma * params.sigma)
            if sqrt_term <= 0:
                continue
            grad["a"] += diff
            grad["b"] += diff * (params.rho * diff_k + sqrt_term)
            grad["rho"] += diff * params.b * diff_k
            grad["m"] += diff * params.b * (params.rho - diff_k / sqrt_term)
            grad["sigma"] += diff * params.b * (params.sigma / sqrt_term)
        penalty = _penalty(params)
        loss += penalty
        if loss < 1e-8:
            break
        params = SVIParams(
            params.a - lr * grad["a"],
            max(1e-6, params.b - lr * grad["b"]),
            max(-0.99, min(0.99, params.rho - lr * grad["rho"])),
            params.m - lr * grad["m"],
            max(1e-4, params.sigma - lr * grad["sigma"]),
        )
    audit("svi_fit", ok=True, params=params.__dict__, points=len(data))
    return params


def implied_vol_surface(params: SVIParams, S: float, K: float, t: float) -> float:
    if t <= 0 or S <= 0 or K <= 0:
        return float("nan")
    k = math.log(K / S)
    total_variance = max(1e-8, _svi_total_variance(params, k))
    return math.sqrt(total_variance / t)


def store_params(params: SVIParams, path: str = "logs/svi_surface.json") -> Path:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ts": float(os.environ.get("EID_TIME", "0")) or 0.0, **params.__dict__}
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


__all__ = ["SVIParams", "fit_svi_arbitrage_free", "implied_vol_surface", "store_params"]
