from __future__ import annotations

import math
import os
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

try:
    from utils.audit import audit_ndjson as audit
except Exception:  # pragma: no cover - dev fallback
    def audit(event: str, **payload):  # type: ignore
        return None

from trading_engine.common.signal_ctx import (
    change_point_prob,
    fetch_hmm,
    fetch_pqre,
    fetch_status,
    ms_vol,
)
from trading_engine.execution.ac_scheduler import almgren_chriss_path
from trading_engine.execution.avellaneda_stoikov import passive_quote
from trading_engine.execution.mixed_policy import choose_mixed_flow
from trading_engine.execution.ow_scheduler import ow_path
from trading_engine.risk.slippage_model import predict_slippage

_DEFAULT_CONFIG = {
    "impact": {"perm": 1.0e-6, "temp": 3.0e-6},
    "ow_resilience": {"rho": 0.15},
    "router": {"risk_aversion": 0.5, "pov_min": 0.05, "pov_max": 0.20},
}
_CONFIG_CACHE: Dict[str, Any] = {"data": None, "ts": 0.0}


def _load_config() -> Dict[str, Any]:
    cached = _CONFIG_CACHE.get("data")
    if cached is not None:
        return cached
    path = Path(os.getenv("TRADING_IMPACT_CONFIG", "trading_engine/config/impact.yaml"))
    if yaml is None or not path.exists():
        _CONFIG_CACHE["data"] = dict(_DEFAULT_CONFIG)
        return _CONFIG_CACHE["data"]
    try:
        cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        cfg = {}
    merged = dict(_DEFAULT_CONFIG)
    for key, value in cfg.items():
        if isinstance(value, dict) and key in merged:
            merged[key].update(value)
        else:
            merged[key] = value
    _CONFIG_CACHE["data"] = merged
    return merged


def _volume_profile(ctx: Dict[str, Any], steps: int) -> List[float]:
    profile = ctx.get("volume_profile")
    if isinstance(profile, Sequence):
        values = [float(v) for v in profile][:steps]
        if len(values) == steps:
            return values
    # default U-shape intraday profile
    return [0.5 + math.sin((idx + 1) / float(steps) * math.pi) for idx in range(steps)]


def _style_from_ctx(ctx: Dict[str, Any], gate: str, pqre_info: Dict[str, Any], hmm_info: Dict[str, Any]) -> str:
    mea_hint = ctx.get("mea_hint") or ""
    imbalance = float(ctx.get("imbalance", 0.0))
    noise = float(pqre_info.get("field", {}).get("params", {}).get("noise", 0.3))
    regime = int(hmm_info.get("regime", 0))
    if abs(imbalance) > 0.6:
        return "LIQ-SNIPE"
    if mea_hint in {"VWAP", "POV", "TWAP"}:
        return mea_hint
    if gate != "ALLOW" or regime > 1 or noise > 0.45:
        return "TWAP"
    return "POV"


def _randomizer(noise: float, seed: Optional[int]) -> float:
    rng = random.Random(seed or int(time.time()))
    return 1.0 + rng.uniform(-0.10 * noise, 0.10 * noise)


def _expected_cost(schedule: List[Dict[str, Any]], side: str, venue: str, urgency: float, model: Optional[Dict[str, Any]]) -> float:
    if not schedule:
        return predict_slippage({"side": side, "venue": venue, "urgency": urgency}, model)
    qty_total = sum(abs(child.get("qty", 0.0)) for child in schedule) or 1.0
    impact_cost = sum(max(0.0, child.get("impact_cost", 0.0)) for child in schedule)
    order_ctx = {"side": side, "venue": venue, "urgency": urgency}
    slippage_bps = predict_slippage(order_ctx, model)
    impact_bps = impact_cost / qty_total * 10000.0
    return slippage_bps + impact_bps


def _expected_cost_mixed(orders: List[Dict[str, Any]], side: str, venue: str, urgency: float, model: Optional[Dict[str, Any]]) -> float:
    if not orders:
        return 0.0
    total_qty = sum(abs(order.get("qty", 0.0)) for order in orders) or 1.0
    impact_cost = 0.0
    for order in orders:
        if order.get("type") == "market":
            hint = order.get("impact_hint") or {}
            temp = abs(float(hint.get("temp", 0.0)))
            perm = abs(float(hint.get("perm", 0.0)))
            impact_cost += abs(float(order.get("qty", 0.0))) * (temp + perm)
    slippage = predict_slippage({"side": side, "venue": venue, "urgency": urgency}, model)
    return slippage + impact_cost / total_qty * 10000.0


def choose_schedule(mode: str, ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ctx = ctx or {}
    cfg = _load_config()
    qty = abs(float(ctx.get("quantity", 0.0)))
    if qty <= 0:
        return {"orders": [], "expected_cost_bps": 0.0, "mode": mode, "style": "NONE"}
    side = ctx.get("side", "buy")
    horizon = float(ctx.get("horizon_minutes", 30.0))
    steps = max(1, int(ctx.get("slices", max(4, int(horizon / 5.0)))) )
    sigma = max(1e-4, float(ctx.get("sigma", 0.25)))
    urgency = float(ctx.get("urgency", 0.5))
    profile = _volume_profile(ctx, steps)
    pqre_info = fetch_pqre()
    hmm_info = fetch_hmm()
    status = fetch_status()
    gate = status.get("gate", "HOLD")

    perm = float(cfg.get("impact", {}).get("perm", 1.0e-6))
    temp = float(cfg.get("impact", {}).get("temp", 3.0e-6))
    rho = float(cfg.get("ow_resilience", {}).get("rho", 0.15))
    lam = float(ctx.get("risk_aversion", cfg.get("router", {}).get("risk_aversion", 0.5)))

    cp_stats = change_point_prob()
    msgarch = ms_vol()
    resilience_score = sigma * rho
    inventory = float(ctx.get("inventory", 0.0))
    passive_hint = ctx.get("execution_hint", "").upper() == "PASSIVE"
    force_mode = (ctx.get("mode") or mode or "").upper()
    inventory_risk = abs(inventory) * max(msgarch.get("sigma", sigma), sigma)

    if force_mode in {"AC", "OW", "MIXED"}:
        decision_mode = force_mode
    else:
        if passive_hint or inventory_risk > 1.5:
            decision_mode = "MIXED"
        elif cp_stats.get("p_change", 0.0) > 0.35 and resilience_score < 0.05:
            decision_mode = "OW"
        elif resilience_score < 0.03:
            decision_mode = "OW"
        elif msgarch.get("sigma", sigma) > 0.65:
            decision_mode = "AC"
        else:
            decision_mode = "AC"

    schedule: List[Dict[str, Any]] = []
    quote_hint: Optional[Dict[str, Any]] = None
    mixed_plan: Optional[Dict[str, Any]] = None

    if decision_mode == "OW":
        schedule = ow_path(qty, horizon, steps, sigma, rho, temp, profile)
    elif decision_mode == "AC":
        schedule = almgren_chriss_path(qty, horizon, steps, sigma, lam, perm, temp, profile)
    else:  # MIXED
        fill_prob = float(ctx.get("fill_prob", 0.55))
        mixed_plan = choose_mixed_flow(
            {
                **ctx,
                "gate": gate,
                "sovereign_gate": status.get("sovereign_gate", gate),
            },
            fill_prob,
            impact_params={"temp": temp, "perm": perm},
        )

    # Avellaneda–Stoikov quote hint when inventory risk elevated or passive request
    if decision_mode == "MIXED" or passive_hint or inventory_risk > 1.5:
        mid_price = float(ctx.get("mid_price", ctx.get("reference_price", 0.0)))
        if mid_price > 0:
            kappa = float(ctx.get("kappa", 1.4))
            horizon_hours = max(1.0 / 12.0, horizon / 60.0)
            quote_hint = passive_quote(mid_price, inventory, sigma, kappa, horizon_hours, lam)

    style = _style_from_ctx(ctx, gate, pqre_info, hmm_info)
    noise = float(pqre_info.get("field", {}).get("params", {}).get("noise", 0.3))
    randomization = _randomizer(noise, ctx.get("seed"))
    router_cfg = cfg.get("router", {})
    pov_min = float(router_cfg.get("pov_min", 0.05))
    pov_max = float(router_cfg.get("pov_max", 0.20))
    pov = max(pov_min, min(pov_max, pov_min + (pov_max - pov_min) * urgency * randomization))

    orders: List[Dict[str, Any]] = []
    passive_share = 0.0
    if decision_mode == "MIXED":
        if mixed_plan is None:
            mixed_plan = choose_mixed_flow(
                {
                    **ctx,
                    "gate": gate,
                    "sovereign_gate": status.get("sovereign_gate", gate),
                },
                float(ctx.get("fill_prob", 0.55)),
                impact_params={"temp": temp, "perm": perm},
            )
        orders = list(mixed_plan.get("orders", []))
        passive_share = float(mixed_plan.get("passive_share", 0.0))
        if "randomization" in mixed_plan:
            randomization = float(mixed_plan.get("randomization", randomization))
        expected_cost = _expected_cost_mixed(
            orders,
            side=side,
            venue=ctx.get("venue", "dark"),
            urgency=urgency,
            model=ctx.get("slippage_model"),
        )
    else:
        for child in schedule:
            qty_child = child.get("qty", 0.0) * randomization
            orders.append(
                {
                    "t": child.get("t"),
                    "qty": qty_child,
                    "style": style,
                    "pov": pov if style == "POV" else None,
                    "mode": decision_mode,
                }
            )
        expected_cost = _expected_cost(
            schedule,
            side=side,
            venue=ctx.get("venue", "dark"),
            urgency=urgency,
            model=ctx.get("slippage_model"),
        )
    risk = {
        "variance": sigma * sigma,
        "regime": hmm_info.get("regime"),
        "gate": gate,
    }
    plan = {
        "mode": decision_mode,
        "style": style,
        "orders": orders,
        "expected_cost_bps": expected_cost,
        "randomization": randomization,
        "risk": risk,
        "notes": ctx.get("notes", ""),
        "passive_share": passive_share,
        "quote_hint": quote_hint,
        "change_point": cp_stats,
        "ms_vol": msgarch,
    }
    audit(
        "exe_plan_v2",
        mode=decision_mode,
        style=style,
        gate=gate,
        expected_cost_bps=expected_cost,
        qty=qty,
        passive_share=passive_share,
        regime=hmm_info.get("regime"),
    )
    return plan


__all__ = ["choose_schedule"]
