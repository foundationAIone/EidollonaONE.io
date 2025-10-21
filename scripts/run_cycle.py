"""Paper trading cycle harness for SE4.3 bring-up."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_router() -> Any:
    router_cls = getattr(import_module("trading_engine.router_effective_price"), "EffectivePriceRouter")
    adapters = [
        getattr(import_module("trading_engine.adapters.kraken"), "KrakenAdapter")(),
        getattr(import_module("trading_engine.adapters.coinbase"), "CoinbaseAdapter")(),
        getattr(import_module("trading_engine.adapters.alpaca"), "AlpacaAdapter")(),
    ]
    return router_cls(adapters)


def _load_bots(config_path: str) -> List[Any]:
    loader = getattr(import_module("bots.registry"), "load_bots")
    return loader(config_path)


def _drive_bot(bot: Any, router: Any, fill: Dict[str, Any]) -> None:
    name = getattr(bot, "name", bot.__class__.__name__)
    if name == "arb_detector" and hasattr(bot, "detect_and_propose"):
        payload = {
            "symbol": fill.get("symbol", "BTC/USD"),
            "net_edge_bps": max(15.0, fill.get("edge_bps", 0.0) + 5.0),
            "route": "kraken->coinbase",
        }
        payload.update({"mid": fill.get("avg_price")})
        bot.detect_and_propose(payload)
        return
    if name == "maker_tuner" and hasattr(bot, "plan_quotes"):
        state = {
            "spread_bps": fill.get("spread_bps", 10.0),
            "vol": 1.1,
            "inventory": -0.2,
        }
        bot.plan_quotes(state)
        return
    if name == "latency_guard" and hasattr(bot, "check"):
        metrics = {"rest_rtt_ms": 110, "ws_lag_ms": 85, "err_rate": 0.004}
        bot.check(metrics)
        return
    if name == "slippage_cal" and hasattr(bot, "nightly_update"):
        samples = {"slippage_bps": 11.5, "samples": 240, "window_hours": 24}
        bot.nightly_update(samples)
        return
    if name == "bandit_alloc" and hasattr(bot, "reweight"):
        performance = {"momentum": 0.6, "mean_reversion": 0.3, "arbitrage_cross": 0.55}
        bot.reweight(performance)
        return
    if name == "regime_sentinel" and hasattr(bot, "update"):
        features = {"realized_vol": 1.3, "funding": 0.01, "volume_z": 0.4}
        bot.update(features)
        return
    if name == "pair_sieve" and hasattr(bot, "evaluate"):
        metrics = {
            "liquidity": 0.9,
            "cost_bps": 4.0,
            "latency_penalty": 0.3,
            "diversification": 0.8,
            "venue_parity": 0.95,
        }
        bot.evaluate(metrics)
        return
    if name == "rebalancer" and hasattr(bot, "rebalance"):
        inventories = {"BTC": 0.8, "ETH": 12.0, "USD": 2500.0}
        bot.rebalance(inventories)
        return
    if name == "risk_sentinel" and hasattr(bot, "guard"):
        snapshot = {"daily_loss_usd": -8.0, "max_daily_loss_usd": 20.0, "open_positions": 3}
        bot.guard(snapshot)
        return
    if name == "court_explainer" and hasattr(bot, "explain"):
        detail = {"panel": ["arb_detector", "maker_tuner"], "summary": "Cycle OK"}
        bot.explain("decision-hash-se43", detail)
        return
    if name == "audit_rollup" and hasattr(bot, "nightly"):
        bot.nightly({"events": 12, "q_execute": 1, "maker": 1, "regime": 1})
        return


def run_cycle(config_path: str = "config/bots.yml") -> None:
    router = _load_router()
    fill = router.effective_fill("BTC/USD", "buy", 0.75)
    bots = _load_bots(config_path)
    executed: List[str] = []
    for bot in bots:
        _drive_bot(bot, router, fill)
        executed.append(getattr(bot, "name", bot.__class__.__name__))
    audit_ndjson = getattr(import_module("utils.audit"), "audit_ndjson")
    audit_ndjson(
        "paper_cycle_complete",
        executed=executed,
        ladder=fill.get("ladder"),
        avg_price=fill.get("avg_price"),
        spread_bps=fill.get("spread_bps"),
        reasons=["cycle_complete"],
    )


if __name__ == "__main__":
    run_cycle()
