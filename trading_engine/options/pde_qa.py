from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List

try:
    from utils.audit import audit_ndjson as audit
except Exception:  # pragma: no cover - fallback
    def audit(event: str, **payload: Any) -> None:
        return None

from trading_engine.options import bachelier, bsm, pde_cn


@dataclass
class PDEQAResult:
    price_cn: float
    price_ref: float
    abs_diff: float
    is_outlier: bool


def pde_price_check(
    S: float,
    K: float,
    r: float,
    q: float,
    sigma: float,
    t: float,
    cfg: Dict[str, Any],
) -> PDEQAResult:
    params = {
        "kind": cfg.get("kind", "call"),
        "S0": S,
        "K": K,
        "r": r,
        "q": q,
        "sigma": sigma,
        "T": t,
        "Smax_mult": cfg.get("Smax_mult", 4.0),
        "M": cfg.get("M", 120),
        "N": cfg.get("N", 120),
    }
    price_cn, _ = pde_cn.crank_nicolson_euro(**params)
    model = cfg.get("model", "bsm").lower()
    if model == "bachelier":
        price_ref = bachelier.price(params["kind"], S, K, r, sigma, t)
    else:
        price_ref = bsm.price(params["kind"], S, K, r, q, sigma, t)
    abs_diff = abs(price_cn - price_ref)
    thresh = cfg.get("threshold", 0.75)
    is_outlier = abs_diff > thresh
    audit("pde_qa", S=S, K=K, model=model, diff=abs_diff, outlier=is_outlier)
    return PDEQAResult(price_cn, price_ref, abs_diff, is_outlier)


def batch_check(cases: Iterable[Dict[str, Any]], cfg: Dict[str, Any]) -> List[PDEQAResult]:
    results: List[PDEQAResult] = []
    for case in cases:
        result = pde_price_check(
            case.get("S", 100.0),
            case.get("K", 100.0),
            case.get("r", 0.01),
            case.get("q", 0.0),
            case.get("sigma", 0.2),
            case.get("t", 0.5),
            cfg,
        )
        results.append(result)
    return results


__all__ = ["PDEQAResult", "pde_price_check", "batch_check"]
