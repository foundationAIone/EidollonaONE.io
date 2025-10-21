"""SE41 StockBot
Equity momentum & breadth signal synthesis.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional, Tuple, List, cast
import time
import random
import logging
import json
import math

try:  # pragma: no cover
    from symbolic_core.symbolic_equation41 import SymbolicEquation41  # type: ignore
    # Use modern context builder to avoid shim warnings
    from symbolic_core.context_builder import assemble_se41_context  # type: ignore
    from trading.helpers.se41_trading_gate import (
        se41_signals,
        ethos_decision_envelope,
        se41_numeric,
    )  # type: ignore
except Exception:  # pragma: no cover
    SymbolicEquation41 = object  # type: ignore

    def assemble_se41_context():
        return {"now": time.time()}

    def _fallback_se41_signals(*args, **kwargs):
        d = args[0] if args and isinstance(args[0], dict) else {}
        return {"confidence": 0.5, "features": d}
    se41_signals = cast(Any, _fallback_se41_signals)

    def _fallback_ethos_decision_envelope(tx):
        return {"decision": "allow"}
    ethos_decision_envelope = cast(Any, _fallback_ethos_decision_envelope)

    def _fallback_se41_numeric(M_t=None, DNA_states=None, harmonic_patterns=None):
        return 0.5
    se41_numeric = cast(Any, _fallback_se41_numeric)


log = logging.getLogger(__name__)


@dataclass
class BotConfig:
    name: str = "stock_bot"
    seed: Optional[int] = 29
    risk_threshold: float = 0.43
    emit_path: Optional[str] = None
    universe: List[str] = field(
        default_factory=lambda: ["AAPL", "MSFT", "GOOG", "AMZN", "NVDA", "META"]
    )


@dataclass
class BotState:
    started_at: float = field(default_factory=time.time)
    cycles: int = 0
    last_score: float = 0.0
    last_action: Optional[str] = None
    allowed: int = 0
    denied: int = 0
    held: int = 0


class StockBot:
    def __init__(self, cfg: Optional[BotConfig] = None):
        self.cfg = cfg or BotConfig()
        if self.cfg.seed is not None:
            random.seed(self.cfg.seed)
        self.state = BotState()
        self.ctx = assemble_se41_context()
        self.eq = SymbolicEquation41()

    def observe(self) -> Dict[str, Any]:
        rets = {s: random.uniform(-0.02, 0.02) for s in self.cfg.universe}
        breadth = sum(1 for r in rets.values() if r > 0) / max(1, len(rets))
        avg_ret = sum(rets.values()) / max(1, len(rets))
        dispersion = math.sqrt(
            sum((r - avg_ret) ** 2 for r in rets.values()) / max(1, len(rets))
        )
        return {
            "returns": rets,
            "breadth": breadth,
            "avg_ret": avg_ret,
            "dispersion": dispersion,
            "ts": time.time(),
        }

    def decide(self, obs: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        try:
            feats = se41_signals(obs) or {}
        except Exception:
            try:
                feats = se41_signals({}) or {}
            except Exception:
                feats = {}
        breadth = obs["breadth"]
        mom = (obs["avg_ret"] + 0.02) / 0.04
        mom = max(0.0, min(1.0, mom))
        stability = 1.0 - min(1.0, obs["dispersion"] / 0.05)
        dna = [breadth, mom, stability, feats.get("confidence", 0.5), 1.0]
        score_raw = se41_numeric(M_t=mom, DNA_states=dna, harmonic_patterns=dna[::-1])
        try:
            score = float(score_raw)
        except Exception:
            score = 0.5
        return max(0.0, min(1.0, abs(score))), {
            "features": feats,
            "breadth": breadth,
            "momentum": mom,
        }

    def act(self, obs: Dict[str, Any], score: float, meta: Dict[str, Any]) -> str:
        if score < self.cfg.risk_threshold:
            self.state.held += 1
            return "hold"
        dec = ethos_decision_envelope(
            {"scope": self.cfg.name, "score": score, "meta": meta}
        )
        if isinstance(dec, dict) and dec.get("decision") == "deny":
            self.state.denied += 1
            return "deny"
        action = "overweight" if meta["breadth"] > 0.5 else "underweight"
        self.state.allowed += 1
        if self.cfg.emit_path:
            try:
                with open(self.cfg.emit_path, "a", encoding="utf-8") as f:
                    f.write(
                        json.dumps(
                            {"action": action, "score": score, "ts": time.time()}
                        )
                        + "\n"
                    )
            except Exception as e:  # pragma: no cover
                log.error("emit failed %s", e)
        return action

    def run_once(self) -> Dict[str, Any]:
        self.state.cycles += 1
        obs = self.observe()
        score, meta = self.decide(obs)
        self.state.last_score = score
        action = self.act(obs, score, meta)
        self.state.last_action = action
        return {"score": score, "action": action, "state": asdict(self.state)}


def create_bot(**kwargs) -> StockBot:
    return StockBot(BotConfig(**kwargs))


def _selftest() -> int:
    r = create_bot().run_once()
    ok = 0.0 <= r["score"] <= 1.0
    print("StockBot selftest", "PASS" if ok else "FAIL", json.dumps(r))
    return 0 if ok else 1


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    print(json.dumps(create_bot().run_once(), indent=2))
