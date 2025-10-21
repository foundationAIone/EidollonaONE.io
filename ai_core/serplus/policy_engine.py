"""Serplus Policy Engine (SE41-aligned)

Computes mint / buyback decisions for the Serplus currency using coverage
control with governance gating. This module distinguishes clearly between:

 - Serplus (token) : proper noun, currency logic
 - surplus (economic) : reserve surplus condition

Implements formulas provided in design spec (§2.2 & §3 of user request).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional
import random
import time
import logging

log = logging.getLogger(__name__)

try:  # pragma: no cover
    from symbolic_core.context_builder import assemble_se41_context  # type: ignore
    from trading.helpers.se41_trading_gate import se41_numeric, ethos_decision  # type: ignore
except Exception:  # fallback stubs

    def assemble_se41_context(**kw):
        return {"now": time.time(), **kw}

    def se41_numeric(**_):
        return 0.55

    def ethos_decision(_):
        return {"decision": "allow"}


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


@dataclass
class PolicyInputs:
    reserves_usd: float
    supply: float
    price_usd: float
    twap_usd: float
    realized_vol: float
    liquidity_score: float
    target_coverage: float = 1.2
    alpha: float = 0.2  # mint dampening
    daily_cap: float = 0.02  # 2% of supply
    jitter_sigma: float = 0.02  # ±2%


@dataclass
class PolicyDecision:
    mint_delta: float
    buyback_budget_usd: float
    score: float
    coverage: float
    surplus_ratio: float
    reason: str


def compute_policy(i: PolicyInputs, ctx: Optional[Dict] = None) -> PolicyDecision:
    ctx = ctx or assemble_se41_context()
    eps = 1e-9
    denom = max(i.supply * max(i.twap_usd, i.price_usd, eps), eps)
    coverage = i.reserves_usd / denom
    # surplus condition
    surplus_usd = max(0.0, i.reserves_usd - i.target_coverage * denom)
    deficit_usd = max(0.0, i.target_coverage * denom - i.reserves_usd)
    surplus_ratio = max(0.0, coverage - i.target_coverage) / i.target_coverage

    dna = [
        coverage,
        _clamp01(surplus_ratio),
        _clamp01(i.realized_vol),
        _clamp01(i.liquidity_score),
        1.0,
    ]
    score = abs(
        float(
            se41_numeric(
                M_t=coverage, DNA_states=dna, harmonic_patterns=list(reversed(dna))
            )
        )
    )
    score = _clamp01(score)

    # propose mint (bounded)
    mint_raw = i.alpha * (surplus_usd / max(i.twap_usd, i.price_usd, eps))
    mint_cap = i.daily_cap * i.supply
    mint = min(mint_raw, mint_cap)

    # jitter to reduce predictability
    if mint > 0:
        mint *= 1.0 + random.gauss(0.0, i.jitter_sigma)

    gate = ethos_decision(
        {
            "scope": "serplus_policy",
            "score": score,
            "meta": {"coverage": coverage, "surplus_ratio": surplus_ratio},
        }
    )
    if isinstance(gate, dict) and gate.get("decision") == "deny":
        return PolicyDecision(0.0, 0.0, score, coverage, surplus_ratio, "ethos_denied")

    reason = (
        "surplus_mint"
        if mint > 0
        else ("deficit_buyback" if deficit_usd > 0 else "hold")
    )
    buyback_budget = 0.0
    if deficit_usd > 0:
        buyback_budget = 0.05 * i.reserves_usd  # example weekly budget

    decision = PolicyDecision(
        max(0.0, mint), buyback_budget, score, coverage, surplus_ratio, reason
    )
    log.debug("policy_decision %s", decision)
    return decision


__all__ = ["PolicyInputs", "PolicyDecision", "compute_policy"]

if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    sample = PolicyInputs(
        reserves_usd=1_200_000,
        supply=1_000_000,
        price_usd=1.0,
        twap_usd=1.0,
        realized_vol=0.12,
        liquidity_score=0.7,
    )
    print(compute_policy(sample))
