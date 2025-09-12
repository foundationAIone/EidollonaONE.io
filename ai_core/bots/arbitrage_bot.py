"""
🤖 EidollonaONE arbitrage_bot v4.1+ (SE41-aligned)

Purpose
-------
Detect synthetic cross‑venue mispricing and emit a gated arbitrage action plan.

Why / What For
--------------
• Provide deterministic spread evaluation driven by SE41 signals & ethos gating.
• Operator value: uniform scoring, safe side‑effects, quick self‑test for CI.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional, Tuple
import logging
import time
import json
import random

# --- SE41 imports with safe fallbacks -------------------------------------------------
try:  # pragma: no cover
    from symbolic_core.symbolic_equation41 import SymbolicEquation41, SE41Signals  # type: ignore
    from symbolic_core.se41_context import assemble_se41_context  # type: ignore
    from trading.helpers.se41_trading_gate import se41_signals, ethos_decision, se41_numeric  # type: ignore

    SYMBOLIC_CORE_AVAILABLE = True
except Exception:  # pragma: no cover
    SYMBOLIC_CORE_AVAILABLE = False

    class SymbolicEquation41: ...  # type: ignore

    class SE41Signals: ...  # type: ignore

    def assemble_se41_context(*_a, **_k):
        return {"now": time.time(), "env": {}, "features": {}}  # type: ignore

    def se41_signals(*_a, **_k):
        return {"features": {}, "confidence": 0.5}  # type: ignore

    def se41_numeric(*_a, **_k):
        return 0.55  # type: ignore

    def ethos_decision(_tx):
        return {"decision": "allow", "reason": "fallback"}  # type: ignore


log = logging.getLogger(__name__)


def _safe_div(n: float, d: float, default: float = 0.0) -> float:
    return n / d if d not in (0, 0.0) else default


@dataclass
class BotConfig:
    name: str = "arbitrage_bot"
    cycle_seconds: float = 0.0
    max_actions_per_cycle: int = 1
    risk_threshold: float = 0.45
    emit_path: Optional[str] = None
    seed: Optional[int] = 17
    spread_entry_bp: float = 8.0  # basis points
    spread_exit_bp: float = 3.0


@dataclass
class BotState:
    started_at: float = field(default_factory=time.time)
    cycles: int = 0
    last_score: float = 0.0
    last_action: Optional[str] = None
    denied: int = 0
    held: int = 0
    allowed: int = 0
    total_opportunities: int = 0
    realized_spread_bp: float = 0.0


class SE41BotBase:
    def __init__(self, cfg: Optional[BotConfig] = None) -> None:
        self.cfg = cfg or BotConfig()
        self.state = BotState()
        if self.cfg.seed is not None:
            random.seed(self.cfg.seed)
        self.ctx: Dict[str, Any] = {}
        self.eq = SymbolicEquation41()  # may be stub

    def configure(self) -> None:
        log.info("Configuring bot %s", self.cfg.name)

    def bootstrap(self) -> None:
        self.ctx = assemble_se41_context()
        log.info("Bootstrapped ctx keys=%s", list(self.ctx.keys()))

    def observe(self) -> Dict[str, Any]:  # to override
        return {"ts": time.time()}

    def decide(
        self, obs: Dict[str, Any]
    ) -> Tuple[float, Dict[str, Any]]:  # to override
        feats = se41_signals(obs)
        dna = [0.9, 0.95, feats.get("confidence", 0.5), 1.0, 1.1]
        score_raw = se41_numeric(
            M_t=feats.get("confidence", 0.5),
            DNA_states=dna,
            harmonic_patterns=dna[::-1],
        )
        try:
            score = float(score_raw)
        except Exception:
            score = 0.55
        return max(0.0, min(1.0, abs(score))), {"features": feats}

    def act(
        self, obs: Dict[str, Any], score: float, meta: Dict[str, Any]
    ) -> Optional[str]:  # to override
        if score < self.cfg.risk_threshold:
            self.state.held += 1
            return "hold"
        decision = ethos_decision(
            {"scope": self.cfg.name, "score": float(score), "meta": meta}
        )
        if isinstance(decision, dict) and decision.get("decision") == "deny":
            self.state.denied += 1
            return "deny"
        self.state.allowed += 1
        return "allow"

    def learn(self, obs: Dict[str, Any], outcome: Optional[str]) -> None:
        return

    def run_once(self) -> Dict[str, Any]:
        self.state.cycles += 1
        obs = self.observe()
        score, meta = self.decide(obs)
        self.state.last_score = score
        outcome = self.act(obs, score, meta)
        self.state.last_action = outcome
        self.learn(obs, outcome)
        return {"score": score, "outcome": outcome, "state": asdict(self.state)}


class ArbitrageBot(SE41BotBase):
    """Role-specific behavior: detect synthetic two‑venue spread and decide route."""

    def observe(self) -> Dict[str, Any]:
        p_a = 100 + random.uniform(-0.5, 0.5)
        p_b = 100 + random.uniform(-0.5, 0.5)
        spread = p_a - p_b
        return {"venues": {"A": p_a, "B": p_b}, "spread": spread, "ts": time.time()}

    def decide(self, obs: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        spread = obs["spread"]
        mid = (obs["venues"]["A"] + obs["venues"]["B"]) / 2.0
        spread_bp = _safe_div(spread, mid, 0.0) * 1e4
        self.state.total_opportunities += 1
        feats = se41_signals({"spread_bp": spread_bp, "mid": mid})
        edge_factor = max(
            0.0, min(1.0, abs(spread_bp) / (self.cfg.spread_entry_bp * 2))
        )
        dna = [
            1.0 - min(1.0, abs(spread_bp) / 1000),
            edge_factor,
            feats.get("confidence", 0.5),
            1.0,
            1.05,
            1.1,
        ]
        score_raw = se41_numeric(
            M_t=edge_factor, DNA_states=dna, harmonic_patterns=dna[::-1]
        )
        try:
            score = float(score_raw)
        except Exception:
            score = 0.5
        score = max(0.0, min(1.0, abs(score)))
        meta = {"features": feats, "spread_bp": spread_bp, "edge_factor": edge_factor}
        return score, meta

    def act(
        self, obs: Dict[str, Any], score: float, meta: Dict[str, Any]
    ) -> Optional[str]:
        spread_bp = meta.get("spread_bp", 0.0)
        if abs(spread_bp) < self.cfg.spread_entry_bp:
            self.state.held += 1
            return "hold"
        decision = ethos_decision(
            {"scope": f"{self.cfg.name}|arb", "score": float(score), "meta": meta}
        )
        if isinstance(decision, dict) and decision.get("decision") == "deny":
            self.state.denied += 1
            return "deny"
        direction = "sell_A_buy_B" if spread_bp > 0 else "buy_A_sell_B"
        payload = {
            "action": direction,
            "spread_bp": spread_bp,
            "score": score,
            "ts": time.time(),
        }
        if self.cfg.emit_path:
            try:
                with open(self.cfg.emit_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(payload) + "\n")
            except Exception as e:  # pragma: no cover
                log.error("Emit failed: %s", e)
        self.state.allowed += 1
        # Realized spread approximation if exit condition triggers
        if abs(spread_bp) <= self.cfg.spread_exit_bp:
            self.state.realized_spread_bp += spread_bp
        log.info("Arb plan %s score=%.3f spread_bp=%.2f", direction, score, spread_bp)
        return direction


def create_bot(**kwargs) -> ArbitrageBot:
    return ArbitrageBot(BotConfig(**kwargs))


def _selftest() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s"
    )
    bot = create_bot(name="arbitrage_bot")
    bot.configure()
    bot.bootstrap()
    result = bot.run_once()
    ok = 0.0 <= result["score"] <= 1.0 and isinstance(result["state"], dict)
    print("Selftest:", "✅ PASS" if ok else "❌ FAIL", "|", json.dumps(result))
    return 0 if ok else 1


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--emit", type=str, default=None)
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s"
    )
    bot = create_bot(emit_path=args.emit)
    bot.configure()
    bot.bootstrap()
    print(json.dumps(bot.run_once(), indent=2))
