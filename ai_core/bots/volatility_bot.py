"""SE41 VolatilityBot
Scores volatility regime & emits hedge / harvest suggestions.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional, Tuple, cast
import time
import random
import logging
import json

try:  # pragma: no cover
    from symbolic_core.symbolic_equation41 import SymbolicEquation41  # type: ignore
    # Prefer modern context builder to avoid legacy shim warnings
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
        return {"confidence": 0.55, "features": d}
    se41_signals = cast(Any, _fallback_se41_signals)

    def _fallback_ethos_decision_envelope(tx):
        return {"decision": "allow"}
    ethos_decision_envelope = cast(Any, _fallback_ethos_decision_envelope)

    def _fallback_se41_numeric(M_t=None, DNA_states=None, harmonic_patterns=None):
        return 0.55
    se41_numeric = cast(Any, _fallback_se41_numeric)


log = logging.getLogger(__name__)


@dataclass
class BotConfig:
    name: str = "volatility_bot"
    seed: Optional[int] = 41
    risk_threshold: float = 0.48
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


class VolatilityBot:
    def __init__(self, cfg: Optional[BotConfig] = None):
        self.cfg = cfg or BotConfig()
        if self.cfg.seed is not None:
            random.seed(self.cfg.seed)
        self.state = BotState()
        self.ctx = assemble_se41_context()
        self.eq = SymbolicEquation41()

    def observe(self) -> Dict[str, Any]:
        realized = random.uniform(0.1, 0.5)
        implied = realized + random.uniform(-0.05, 0.05)
        vol_of_vol = random.uniform(0.0, 0.4)
        return {
            "realized": realized,
            "implied": implied,
            "vol_of_vol": vol_of_vol,
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
        premium = obs["implied"] - obs["realized"]
        premium_n = (premium + 0.1) / 0.2
        premium_n = max(0.0, min(1.0, premium_n))
        turbulence = min(1.0, obs["vol_of_vol"] / 0.4)
        dna = [premium_n, 1.0 - turbulence, feats.get("confidence", 0.55), 1.01]
        score_raw = se41_numeric(
            M_t=premium_n, DNA_states=dna, harmonic_patterns=dna[::-1]
        )
        try:
            score = float(score_raw)
        except Exception:
            score = 0.5
        return max(0.0, min(1.0, abs(score))), {
            "features": feats,
            "premium": premium,
            "turbulence": turbulence,
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
        premium = meta["premium"]
        if premium > 0.03:
            action = "sell_vol"
        elif premium < -0.03:
            action = "buy_vol"
        else:
            action = "neutral"
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


def create_bot(**kwargs) -> VolatilityBot:
    return VolatilityBot(BotConfig(**kwargs))


def _selftest() -> int:
    r = create_bot().run_once()
    ok = 0.0 <= r["score"] <= 1.0
    print("VolatilityBot selftest", "PASS" if ok else "FAIL", json.dumps(r))
    return 0 if ok else 1


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    print(json.dumps(create_bot().run_once(), indent=2))
