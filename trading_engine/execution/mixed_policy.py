from __future__ import annotations

import math
import random
import time
from typing import Any, Dict, List, Optional

try:
    from utils.audit import audit_ndjson as audit
except Exception:  # pragma: no cover - development fallback
    def audit(event: str, **payload: Any) -> None:
        return None


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _rng(seed: Optional[int] = None) -> random.Random:
    return random.Random(seed or int(time.time()))


def choose_mixed_flow(
    ctx: Dict[str, Any],
    fill_prob_est: float,
    impact_params: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Generate a mixed limit + market child order plan following Cartea–Jaimungal flow."""

    qty = abs(float(ctx.get("quantity", 0.0)))
    if qty <= 0:
        return {
            "mode": "MIXED",
            "orders": [],
            "passive_share": 0.0,
            "expected_fill": 0.0,
            "randomization": 1.0,
        }

    side = ctx.get("side", "buy")
    risk_aversion = float(ctx.get("risk_aversion", 0.5))
    sovereign_gate = ctx.get("sovereign_gate", ctx.get("gate", "HOLD"))
    urgency = float(ctx.get("urgency", 0.5))
    seed = ctx.get("seed")
    rng = _rng(seed)
    random_noise = 1.0 + rng.uniform(-0.08, 0.08)

    # Passive share influenced by fill estimate, risk aversion, and gate posture
    passive_base = _clip(fill_prob_est, 0.0, 1.0)
    passive_gate = 0.5 if sovereign_gate != "ALLOW" else 1.0
    passive_bias = passive_base * (1.0 - 0.45 * risk_aversion) * passive_gate
    passive_bias *= _clip(1.0 - 0.35 * urgency, 0.15, 1.0)
    passive_share = _clip(passive_bias * random_noise, 0.0, 0.85)
    passive_qty = qty * passive_share
    market_qty = qty - passive_qty

    # Impact parameters to inform market child sizing
    impact = impact_params or {}
    temp_impact = abs(float(impact.get("temp", 3.0e-6)))
    perm_impact = abs(float(impact.get("perm", 1.0e-6)))
    clip_size = max(float(ctx.get("max_clip", qty * 0.4)), 1.0)

    # Limit posting strategy (single or dual post with queue estimates)
    queue_depth = max(float(ctx.get("queue_depth", 20000.0)), 1.0)
    post_count = 2 if passive_qty > clip_size * 0.6 else 1
    limit_children: List[Dict[str, Any]] = []
    if passive_qty > 0:
        per_child = passive_qty / post_count
        for idx in range(post_count):
            price_offset = ctx.get("mid_offset", 0.0) - math.copysign(
                (0.5 - fill_prob_est) * 0.25, 1 if side == "buy" else -1
            )
            limit_children.append(
                {
                    "type": "limit",
                    "side": side,
                    "qty": per_child,
                    "price_offset": price_offset,
                    "queue_estimate": queue_depth * (1.0 - fill_prob_est * 0.6),
                    "venue_hint": ctx.get("venue_hint", "lit"),
                    "randomize": rng.random(),
                }
            )

    # Market child orders split to manage impact exposure
    market_children: List[Dict[str, Any]] = []
    if market_qty > 0:
        market_clips = max(1, int(math.ceil(market_qty / clip_size)))
        per_child = market_qty / market_clips
        for idx in range(market_clips):
            delay = idx * _clip(urgency * 2.0, 0.1, 1.5)
            market_children.append(
                {
                    "type": "market",
                    "side": side,
                    "qty": per_child,
                    "delay": delay,
                    "impact_hint": {
                        "temp": temp_impact,
                        "perm": perm_impact,
                    },
                    "randomize": rng.random(),
                }
            )

    orders = limit_children + market_children
    expected_fill = passive_share * _clip(fill_prob_est * 1.05, 0.0, 1.0)

    plan = {
        "mode": "MIXED",
        "orders": orders,
        "passive_share": passive_share,
        "expected_fill": expected_fill,
        "randomization": random_noise,
        "impact": {"temp": temp_impact, "perm": perm_impact},
    }
    audit(
        "mixed_flow_plan",
        side=side,
        qty=qty,
        passive_share=passive_share,
        expected_fill=expected_fill,
        gate=sovereign_gate,
    )
    return plan


__all__ = ["choose_mixed_flow"]
