"""SE41 DCABot
Dollar-cost averaging bot scheduling allocation pulses with governance gating.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional
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
        return {"confidence": 0.5, "features": d}

    def ethos_decision(tx):
        return {"decision": "allow"}

    def se41_numeric(**_):
        return 0.5


log = logging.getLogger(__name__)


@dataclass
class BotConfig:
    name: str = "dca_bot"
    seed: Optional[int] = 31
    risk_threshold: float = 0.4
    emit_path: Optional[str] = None
    base_amount: float = 100.0


@dataclass
class BotState:
    started_at: float = field(default_factory=time.time)
    cycles: int = 0
    last_score: float = 0.0
    last_action: Optional[str] = None
    allowed: int = 0
    denied: int = 0
    held: int = 0
    total_invested: float = 0.0


class DCABot:
    def __init__(self, cfg: Optional[BotConfig] = None):
        self.cfg = cfg or BotConfig()
        if self.cfg.seed is not None:
            random.seed(self.cfg.seed)
        self.state = BotState()
        self.ctx = assemble_se41_context()
        self.eq = SymbolicEquation41()

    def observe(self) -> Dict[str, Any]:
        price = 50 + random.uniform(-1, 1)
        vol = random.uniform(0.1, 0.4)
        return {"price": price, "vol": vol, "ts": time.time()}

    def decide(self, obs: Dict[str, Any]):
        feats = se41_signals(obs)
        vol = obs["vol"]
        modulation = 1.0 - min(1.0, (vol - 0.1) / 0.3)
        dna = [modulation, feats.get("confidence", 0.5), 1.0]
        score_raw = se41_numeric(
            M_t=modulation, DNA_states=dna, harmonic_patterns=dna[::-1]
        )
        try:
            score = float(score_raw)
        except Exception:
            score = 0.5
        score = max(0.0, min(1.0, abs(score)))
        return score, {"features": feats, "modulation": modulation}

    def act(self, obs: Dict[str, Any], score: float, meta: Dict[str, Any]) -> str:
        if score < self.cfg.risk_threshold:
            self.state.held += 1
            return "hold"
        dec = ethos_decision({"scope": self.cfg.name, "score": score, "meta": meta})
        if isinstance(dec, dict) and dec.get("decision") == "deny":
            self.state.denied += 1
            return "deny"
        amount = self.cfg.base_amount * meta.get("modulation", 1.0)
        self.state.total_invested += amount
        self.state.allowed += 1
        action = f"invest:{amount:.2f}"
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


def create_bot(**kwargs) -> DCABot:
    return DCABot(BotConfig(**kwargs))


def _selftest() -> int:
    r = create_bot().run_once()
    ok = 0.0 <= r["score"] <= 1.0
    print("DCABot selftest", "PASS" if ok else "FAIL", json.dumps(r))
    return 0 if ok else 1


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    print(json.dumps(create_bot().run_once(), indent=2))
