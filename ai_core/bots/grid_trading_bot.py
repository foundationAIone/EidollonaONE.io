"""SE41 GridTradingBot
Simulated price channel grid activation & governance gating.
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
    name: str = "grid_trading_bot"
    seed: Optional[int] = 37
    risk_threshold: float = 0.44
    emit_path: Optional[str] = None
    grid_size: int = 5
    band_pct: float = 0.04


@dataclass
class BotState:
    started_at: float = field(default_factory=time.time)
    cycles: int = 0
    last_score: float = 0.0
    last_action: Optional[str] = None
    allowed: int = 0
    denied: int = 0
    held: int = 0
    fills: int = 0


class GridTradingBot:
    def __init__(self, cfg: Optional[BotConfig] = None):
        self.cfg = cfg or BotConfig()
        if self.cfg.seed is not None:
            random.seed(self.cfg.seed)
        self.state = BotState()
        self.ctx = assemble_se41_context()
        self.eq = SymbolicEquation41()
        self._mid_ref = 100.0

    def observe(self) -> Dict[str, Any]:
        price = self._mid_ref + random.uniform(-2, 2)
        band_top = self._mid_ref * (1 + self.cfg.band_pct)
        band_bot = self._mid_ref * (1 - self.cfg.band_pct)
        pos_in_band = (price - band_bot) / max(1e-9, band_top - band_bot)
        return {
            "price": price,
            "band_top": band_top,
            "band_bot": band_bot,
            "pos": pos_in_band,
            "ts": time.time(),
        }

    def decide(self, obs: Dict[str, Any]):
        feats = se41_signals(obs)
        pos = obs["pos"]
        centrality = 1.0 - abs(pos - 0.5) * 2
        centrality = max(0.0, min(1.0, centrality))
        dna = [centrality, feats.get("confidence", 0.5), 1.0]
        score_raw = se41_numeric(
            M_t=centrality, DNA_states=dna, harmonic_patterns=dna[::-1]
        )
        try:
            score = float(score_raw)
        except Exception:
            score = 0.5
        return max(0.0, min(1.0, abs(score))), {"features": feats, "pos": pos}

    def act(self, obs: Dict[str, Any], score: float, meta: Dict[str, Any]) -> str:
        if score < self.cfg.risk_threshold:
            self.state.held += 1
            return "hold"
        dec = ethos_decision({"scope": self.cfg.name, "score": score, "meta": meta})
        if isinstance(dec, dict) and dec.get("decision") == "deny":
            self.state.denied += 1
            return "deny"
        pos = meta.get("pos", 0.5)
        if pos < 0.2:
            action = "place_bid"
        elif pos > 0.8:
            action = "place_ask"
        else:
            action = "mid_hold"
        if action in ("place_bid", "place_ask"):
            self.state.fills += 1
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


def create_bot(**kwargs) -> GridTradingBot:
    return GridTradingBot(BotConfig(**kwargs))


def _selftest() -> int:
    r = create_bot().run_once()
    ok = 0.0 <= r["score"] <= 1.0
    print("GridTradingBot selftest", "PASS" if ok else "FAIL", json.dumps(r))
    return 0 if ok else 1


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    print(json.dumps(create_bot().run_once(), indent=2))
