"""Sequential historical bar replay simulator (SE41 v4.1+ aligned)

Enhancements vs prior version:
	* Optional SE41 context assembly & signal extraction (if available)
	* Latency measurement (ms) for full pass
	* Ethos gating with deny/hold neutralization
	* Strategy callback isolation with safe error capture (records error count)
	* Deterministic numeric fallback when SE41 helpers absent
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Callable, Dict, Optional, Any
from time import perf_counter

try:  # soft import governance helpers
    from trading.helpers.se41_trading_gate import (
        se41_numeric,
        ethos_decision,
        se41_signals,
    )  # type: ignore
except Exception:  # pragma: no cover

    def se41_numeric(**_kw):  # type: ignore
        return {"score": 0.55}

    def ethos_decision(_tx):  # type: ignore
        return {"decision": "allow"}

    def se41_signals(_ctx):  # type: ignore
        return {"coherence": 0.55}


try:  # context builder optional
    from symbolic_core.se41_context import assemble_se41_context  # type: ignore
except Exception:  # pragma: no cover

    def assemble_se41_context(**kw):  # type: ignore
        return {
            "perception": kw.get("perception", {}),
            "intent": kw.get("intent", {}),
            "mirror": kw.get("mirror", {}),
            "substrate": kw.get("substrate", {"S_EM": 0.8}),
        }


@dataclass
class Bar:
    ts: float
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class HistoricalSimulator:
    """Pluggable strategy callback over bars with optional SE41 context.

    strategy_fn(bar, state) -> Optional[Dict]
    Returned dict may have keys:
      * signal: +1/-1/0
      * leverage: float (advisory)
      * meta: arbitrary strategy metadata
    """

    def __init__(
        self,
        bars: Iterable[Bar],
        strategy_fn: Callable[[Bar, Dict], Optional[Dict]],
        risk_leverage_limit: float = 5.0,
        use_context: bool = False,
    ) -> None:
        self.bars = list(bars)
        self.strategy_fn = strategy_fn
        self.risk_leverage_limit = risk_leverage_limit
        self.use_context = use_context
        self.state: Dict[str, Any] = {"positions": {}, "signals": [], "errors": 0}
        self.metrics: Dict[str, Any] = {
            "processed": 0,
            "ethos_holds": 0,
            "ethos_denies": 0,
            "latency_ms": 0.0,
        }

    def run(self, ctx_seed: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = perf_counter()
        ctx = None
        if self.use_context:
            if ctx_seed is None:
                ctx_seed = {
                    "perception": {"mode": "hist"},
                    "intent": {"objective": "replay"},
                    "mirror": {"consistency": 0.72},
                    "substrate": {"S_EM": 0.81},
                }
            ctx = assemble_se41_context(**ctx_seed)

        for bar in self.bars:
            try:
                out = self.strategy_fn(bar, self.state) or {}
            except Exception:  # strategy isolation
                self.state["errors"] += 1
                out = {}
            sig = out.get("signal")
            lev = float(abs(out.get("leverage", 1.0)))
            if lev > self.risk_leverage_limit:
                lev = self.risk_leverage_limit
            numeric = se41_numeric(M_t=0.59, DNA_states=[1.0, lev, 1.0, 1.08])
            # Optionally enrich numeric with context coherence
            if ctx is not None:
                coh = se41_signals(ctx).get("coherence", 0.55)
                numeric_score = (numeric.get("score", 0.55) + coh) / 2.0
            else:
                numeric_score = numeric.get("score", 0.55)
            decision = ethos_decision(
                {"scope": "hist_bar", "lev": lev, "score": numeric_score}
            )
            gate = (
                decision.get("decision", "allow")
                if isinstance(decision, dict)
                else "allow"
            )
            if gate == "deny":
                self.metrics["ethos_denies"] += 1
                sig = 0
            elif gate == "hold":
                self.metrics["ethos_holds"] += 1
                sig = 0
            if sig:
                self.state["signals"].append(
                    {"ts": bar.ts, "symbol": bar.symbol, "signal": sig}
                )
            self.metrics["processed"] += 1

        self.metrics["latency_ms"] = round((perf_counter() - start) * 1000.0, 3)
        return {
            "state": self.state,
            "metrics": self.metrics,
            "context_used": self.use_context,
        }


__all__ = ["HistoricalSimulator", "Bar"]
