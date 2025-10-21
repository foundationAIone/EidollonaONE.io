from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Sequence

try:
    from utils.audit import audit_ndjson as audit
except Exception:  # pragma: no cover - fallback
    def audit(event: str, **payload: Any) -> None:
        return None


def _sanitize(series: Iterable[float], max_T: int) -> List[float]:
    values: List[float] = []
    for value in series:
        try:
            values.append(float(value))
        except Exception:
            continue
        if len(values) >= max_T:
            break
    return values[-max_T:]


def _student_t_pdf(x: float, mean: float, scale: float, dof: float) -> float:
    scale = max(1e-8, float(scale))
    dof = max(1e-6, float(dof))
    coeff = math.lgamma((dof + 1.0) / 2.0) - math.lgamma(dof / 2.0)
    coeff -= 0.5 * math.log(dof * math.pi) + math.log(scale)
    power = -((dof + 1.0) / 2.0) * math.log1p(((x - mean) ** 2) / (dof * scale * scale))
    return math.exp(coeff + power)


def _update_posterior(mu: float, k: float, alpha: float, beta: float, x: float) -> Dict[str, float]:
    k_n = k + 1.0
    mu_n = (k * mu + x) / k_n
    alpha_n = alpha + 0.5
    beta_n = beta + (k * (x - mu) ** 2) / (2.0 * k_n)
    return {"mu": mu_n, "k": k_n, "alpha": alpha_n, "beta": beta_n}


def bocpd_posterior(
    returns: Sequence[float],
    hazard: float = 0.01,
    mu0: float = 0.0,
    k0: float = 1.0,
    alpha0: float = 1.0,
    beta0: float = 1.0,
    max_T: int = 2000,
) -> Dict[str, Any]:
    series = _sanitize(returns, max_T)
    T = len(series)
    if T == 0:
        return {"p_change": 0.0, "run_length": 0, "probs": []}

    hazard = min(max(hazard, 1e-6), 0.5)
    log_h = math.log(hazard)
    log_1mh = math.log(1.0 - hazard)

    log_R = [[-math.inf for _ in range(T + 1)] for _ in range(T + 1)]
    log_R[0][0] = 0.0
    params = [[{"mu": mu0, "k": k0, "alpha": alpha0, "beta": beta0} for _ in range(T + 1)] for _ in range(T + 1)]

    for t in range(1, T + 1):
        x = series[t - 1]
        for r in range(t):
            post = params[t - 1][r]
            mu = post["mu"]
            k = post["k"]
            alpha = post["alpha"]
            beta = post["beta"]
            dof = 2.0 * alpha
            scale = math.sqrt(beta * (k + 1.0) / (alpha * k))
            pred = _student_t_pdf(x, mu, scale, dof)
            if pred <= 0:
                continue
            log_pred = math.log(pred)
            growth = log_R[t - 1][r] + log_1mh + log_pred
            if growth > log_R[t][r + 1]:
                log_R[t][r + 1] = growth
                params[t][r + 1] = _update_posterior(mu, k, alpha, beta, x)

        # Changepoint probability accumulates all previous run lengths
        log_cp = -math.inf
        for r in range(t):
            post = params[t - 1][r]
            mu = post["mu"]
            k = post["k"]
            alpha = post["alpha"]
            beta = post["beta"]
            dof = 2.0 * alpha
            scale = math.sqrt(beta * (k + 1.0) / (alpha * k))
            pred = _student_t_pdf(x, mu, scale, dof)
            if pred <= 0:
                continue
            log_pred = math.log(pred)
            candidate = log_R[t - 1][r] + log_h + log_pred
            if candidate > log_cp:
                log_cp = candidate
        log_R[t][0] = log_cp
        params[t][0] = _update_posterior(mu0, k0, alpha0, beta0, x)

    last_row = log_R[T]
    max_log = max(last_row)
    probs = [math.exp(v - max_log) if v > -math.inf else 0.0 for v in last_row]
    norm = sum(probs) or 1.0
    probs = [p / norm for p in probs]
    p_change = probs[0]
    run_length_est = 0.0
    for idx, prob in enumerate(probs):
        run_length_est += idx * prob
    result = {"p_change": float(min(1.0, p_change)), "run_length": int(round(run_length_est)), "probs": probs}
    audit("bocpd_eval", size=T, hazard=hazard, p_change=result["p_change"], run_length=result["run_length"])
    return result


__all__ = ["bocpd_posterior"]
