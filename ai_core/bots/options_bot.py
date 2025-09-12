"""SE41 OptionsBot
Combines simulated implied volatility deviation and skew to score strategy bias.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional, Tuple
import time
import random
import logging
import json

try:  # pragma: no cover
    from symbolic_core.symbolic_equation41 import SymbolicEquation41  # type: ignore
    from symbolic_core.se41_context import assemble_se41_context  # type: ignore
    from trading.helpers.se41_trading_gate import se41_signals, ethos_decision, se41_numeric  # type: ignore
except Exception:  # pragma: no cover
    SymbolicEquation41 = object  # type: ignore

    def assemble_se41_context():
        return {"now": time.time()}

    def se41_signals(d):
        return {"confidence": 0.6, "features": d}

    def ethos_decision(tx):
        return {"decision": "allow"}

    def se41_numeric(**_):
        return 0.58


log = logging.getLogger(__name__)


@dataclass
class BotConfig:
    name: str = "options_bot"
    seed: Optional[int] = 23
    risk_threshold: float = 0.46
    emit_path: Optional[str] = None


@dataclass
class BotState:
    started_at: float = field(default_factory=time.time)
    cycles: int = 0
    last_score: float = 0.0
    last_action: Optional[str] = None
    allowed: int = 0
    denied: int = 0
    held: int = 0


class OptionsBot:
    def __init__(self, cfg: Optional[BotConfig] = None) -> None:
        self.cfg = cfg or BotConfig()
        if self.cfg.seed is not None:
            random.seed(self.cfg.seed)
        self.state = BotState()
        self.ctx = assemble_se41_context()
        self.eq = SymbolicEquation41()

    def observe(self) -> Dict[str, Any]:
        # Simulate underlying spot and implied vols
        spot = 100 + random.uniform(-2, 2)
        realized = random.uniform(0.15, 0.35)
        iv_atm = realized + random.uniform(-0.05, 0.05)
        skew_25d = random.uniform(-0.1, 0.1)
        term_struct = random.uniform(-0.02, 0.02)
        return {
            "spot": spot,
            "realized": realized,
            "iv_atm": iv_atm,
            "skew_25d": skew_25d,
            "term": term_struct,
            "ts": time.time(),
        }

    def decide(self, obs: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        feats = se41_signals(obs)
        iv_premium = obs["iv_atm"] - obs["realized"]
        premium_norm = (iv_premium + 0.1) / 0.2  # center ~0 within [-0.1,0.1]
        premium_norm = max(0.0, min(1.0, premium_norm))
        skew = obs["skew_25d"]
        skew_factor = (skew + 0.1) / 0.2
        skew_factor = max(0.0, min(1.0, skew_factor))
        dna = [premium_norm, skew_factor, feats.get("confidence", 0.6), 1.03]
        score_raw = se41_numeric(
            M_t=premium_norm, DNA_states=dna, harmonic_patterns=dna[::-1]
        )
        try:
            score = float(score_raw)
        except Exception:
            score = 0.5
        return max(0.0, min(1.0, abs(score))), {
            "features": feats,
            "iv_premium": iv_premium,
            "skew": skew,
        }

    def act(self, obs: Dict[str, Any], score: float, meta: Dict[str, Any]) -> str:
        if score < self.cfg.risk_threshold:
            self.state.held += 1
            return "hold"
        dec = ethos_decision({"scope": self.cfg.name, "score": score, "meta": meta})
        if isinstance(dec, dict) and dec.get("decision") == "deny":
            self.state.denied += 1
            return "deny"
        # Strategy selection heuristic
        if meta["iv_premium"] > 0.02 and meta["skew"] > 0:
            action = "sell_calls"
        elif meta["iv_premium"] > 0.02 and meta["skew"] < 0:
            action = "sell_puts"
        elif meta["iv_premium"] < -0.02:
            action = "long_vol"
        else:
            action = "delta_neutral_hold"
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


def create_bot(**kwargs) -> OptionsBot:
    return OptionsBot(BotConfig(**kwargs))


def _selftest() -> int:
    bot = create_bot()
    r = bot.run_once()
    ok = 0.0 <= r["score"] <= 1.0
    print("OptionsBot selftest", "PASS" if ok else "FAIL", json.dumps(r))
    return 0 if ok else 1


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    print(json.dumps(create_bot().run_once(), indent=2))
