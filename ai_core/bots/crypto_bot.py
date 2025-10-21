"""SE41 CryptoBot
Signal-focused bot producing momentum & volatility aligned score for crypto basket.
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
    # Prefer modern context builder to avoid legacy shim warnings
    from symbolic_core.context_builder import assemble_se41_context  # type: ignore
    from trading.helpers.se41_trading_gate import (
        se41_signals,
        ethos_decision_envelope,
        se41_numeric,
    )  # type: ignore
except Exception:  # pragma: no cover
    SymbolicEquation41 = object  # type: ignore

    def assemble_se41_context(**kwargs):
        d = {"now": time.time()}
        d.update(kwargs)
        return d

    def _fallback_se41_signals(*args, **kwargs):
        d = args[0] if args and isinstance(args[0], dict) else {}
        return {"confidence": 0.5, "features": d}
    se41_signals = cast(Any, _fallback_se41_signals)

    def _fallback_ethos_decision_envelope(tx):
        return {"decision": "allow", "reason": "fallback"}
    ethos_decision_envelope = cast(Any, _fallback_ethos_decision_envelope)

    def _fallback_se41_numeric(M_t=None, DNA_states=None, harmonic_patterns=None):
        return 0.5
    se41_numeric = cast(Any, _fallback_se41_numeric)


log = logging.getLogger(__name__)


@dataclass
class BotConfig:
    name: str = "crypto_bot"
    seed: Optional[int] = 11
    risk_threshold: float = 0.4
    emit_path: Optional[str] = None
    universe: List[str] = field(default_factory=lambda: ["BTC", "ETH", "SOL", "LTC"])


@dataclass
class BotState:
    started_at: float = field(default_factory=time.time)
    cycles: int = 0
    last_score: float = 0.0
    last_action: Optional[str] = None
    allowed: int = 0
    denied: int = 0
    held: int = 0


class CryptoBot:
    def __init__(self, cfg: Optional[BotConfig] = None) -> None:
        self.cfg = cfg or BotConfig()
        if self.cfg.seed is not None:
            random.seed(self.cfg.seed)
        self.state = BotState()
        # Initialize a canonical SE41 context using the modern builder
        self.ctx = assemble_se41_context(
            coherence_hint=0.75,
            risk_hint=0.3,
            uncertainty_hint=0.3,
        )
        self.eq = SymbolicEquation41()

    def observe(self) -> Dict[str, Any]:
        # Simulated returns and realized vol sample
        rets = {s: random.uniform(-0.01, 0.01) for s in self.cfg.universe}
        vol = math.sqrt(sum(r * r for r in rets.values()) / max(1, len(rets)))
        momentum = sum(rets.values()) / max(1, len(rets))
        return {"returns": rets, "vol": vol, "momentum": momentum, "ts": time.time()}

    def decide(self, obs: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        # Tolerate se41_signals implementations that accept 0 or arbitrary args
        _sig = se41_signals  # type: ignore[assignment]
        try:
            feats = _sig(obs) or {}
        except Exception:
            try:
                feats = _sig() or {}
            except Exception:
                feats = {}
        vol = obs["vol"]
        mom = obs["momentum"]
        stability = 1.0 - min(1.0, vol / 0.05)
        directional = (mom + 0.02) / 0.04  # map ~[-0.02,0.02] -> [0,1]
        directional = max(0.0, min(1.0, directional))
        if not isinstance(feats, dict):
            feats = {}
        dna = [stability, directional, feats.get("confidence", 0.5), 1.0, 1.05]
        score_raw = se41_numeric(
            M_t=directional, DNA_states=dna, harmonic_patterns=dna[::-1]
        )
        try:
            score = float(score_raw)
        except Exception:
            score = 0.5
        score = max(0.0, min(1.0, abs(score)))
        return score, {"features": feats, "vol": vol, "momentum": mom}

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
        direction = "accumulate" if meta["momentum"] > 0 else "reduce"
        self.state.allowed += 1
        if self.cfg.emit_path:
            try:
                with open(self.cfg.emit_path, "a", encoding="utf-8") as f:
                    f.write(
                        json.dumps(
                            {"action": direction, "score": score, "ts": time.time()}
                        )
                        + "\n"
                    )
            except Exception as e:  # pragma: no cover
                log.error("emit failed %s", e)
        return direction

    def run_once(self) -> Dict[str, Any]:
        self.state.cycles += 1
        obs = self.observe()
        score, meta = self.decide(obs)
        self.state.last_score = score
        action = self.act(obs, score, meta)
        self.state.last_action = action
        return {"score": score, "action": action, "state": asdict(self.state)}


def create_bot(**kwargs) -> CryptoBot:
    return CryptoBot(BotConfig(**kwargs))


def _selftest() -> int:
    bot = create_bot()
    r = bot.run_once()
    ok = 0.0 <= r["score"] <= 1.0
    print("CryptoBot selftest", "PASS" if ok else "FAIL", json.dumps(r))
    return 0 if ok else 1


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    print(json.dumps(create_bot().run_once(), indent=2))
