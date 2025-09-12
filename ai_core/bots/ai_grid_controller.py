"""SE41 AIGridControllerBot
Adaptive controller supervising grid parameters (band width, level count) and
emitting governance‑gated adjustment intents.

Role
----
Supervisor/Maker hybrid: tunes grid configuration in response to volatility and
price drift, rather than placing direct orders.
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
        return {"confidence": 0.55, "features": d}

    def ethos_decision(tx):
        return {"decision": "allow"}

    def se41_numeric(**_):
        return 0.55


log = logging.getLogger(__name__)


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


@dataclass
class BotConfig:
    name: str = "ai_grid_controller_bot"
    seed: Optional[int] = 53
    risk_threshold: float = 0.45
    emit_path: Optional[str] = None
    base_levels: int = 7
    base_band_pct: float = 0.05
    min_levels: int = 3
    max_levels: int = 15
    min_band_pct: float = 0.01
    max_band_pct: float = 0.12


@dataclass
class BotState:
    started_at: float = field(default_factory=time.time)
    cycles: int = 0
    last_score: float = 0.0
    last_action: Optional[str] = None
    allowed: int = 0
    denied: int = 0
    held: int = 0
    current_levels: int = 0
    current_band_pct: float = 0.0
    adjustments: int = 0


class AIGridControllerBot:
    def __init__(self, cfg: Optional[BotConfig] = None) -> None:
        self.cfg = cfg or BotConfig()
        if self.cfg.seed is not None:
            random.seed(self.cfg.seed)
        self.state = BotState(
            current_levels=self.cfg.base_levels, current_band_pct=self.cfg.base_band_pct
        )
        self.ctx = assemble_se41_context()
        self.eq = SymbolicEquation41()
        self._mid_ref = 100.0

    # --- Lifecycle ------------------------------------------------------------
    def observe(self) -> Dict[str, Any]:
        # Simulate anchor price and realized micro-volatility proxy.
        price = self._mid_ref + random.uniform(-2, 2)
        vol_window = random.uniform(0.05, 0.6)  # pseudo realized volatility
        drift = (price - self._mid_ref) / self._mid_ref
        imbalance = random.uniform(-0.3, 0.3)  # pseudo order book imbalance
        return {
            "price": price,
            "vol": vol_window,
            "drift": drift,
            "imbalance": imbalance,
            "ts": time.time(),
        }

    def decide(self, obs: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        feats = se41_signals(obs)
        vol = obs["vol"]
        drift = obs["drift"]
        # Normalize features
        vol_norm = _clamp((vol - 0.05) / 0.55)
        drift_abs = abs(drift)
        drift_norm = _clamp(drift_abs / 0.08)
        # Lower vol -> tighter band, fewer levels adjust slower; high vol -> widen band, maybe more levels
        tightness = 1.0 - vol_norm  # higher when calmer
        stability = 1.0 - min(1.0, vol_norm * 0.7 + drift_norm * 0.3)
        dna = [tightness, stability, feats.get("confidence", 0.55), 1.0, 1.02]
        score_raw = se41_numeric(
            M_t=stability, DNA_states=dna, harmonic_patterns=dna[::-1]
        )
        try:
            score = float(score_raw)
        except Exception:
            score = 0.5
        score = _clamp(abs(score))
        meta = {
            "features": feats,
            "vol_norm": vol_norm,
            "drift_norm": drift_norm,
            "tightness": tightness,
            "stability": stability,
        }
        return score, meta

    def _proposed_levels(self, vol_norm: float) -> int:
        # More levels when volatility is moderate (not extreme) to capture oscillations.
        target = self.cfg.base_levels + int((0.5 - abs(vol_norm - 0.5)) * 6)
        return max(self.cfg.min_levels, min(self.cfg.max_levels, target))

    def _proposed_band(self, vol_norm: float, drift_norm: float) -> float:
        # Vol widens; strong directional drift widens slightly for safety.
        base = self.cfg.base_band_pct * (0.6 + vol_norm * 0.8)
        drift_expansion = 1.0 + 0.4 * drift_norm
        band = base * drift_expansion
        return max(self.cfg.min_band_pct, min(self.cfg.max_band_pct, band))

    def act(self, obs: Dict[str, Any], score: float, meta: Dict[str, Any]) -> str:
        if score < self.cfg.risk_threshold:
            self.state.held += 1
            return "hold"
        decision = ethos_decision(
            {"scope": self.cfg.name, "score": score, "meta": meta}
        )
        if isinstance(decision, dict) and decision.get("decision") == "deny":
            self.state.denied += 1
            return "deny"
        prop_levels = self._proposed_levels(meta["vol_norm"])
        prop_band = self._proposed_band(meta["vol_norm"], meta["drift_norm"])
        changed = (prop_levels != self.state.current_levels) or (
            abs(prop_band - self.state.current_band_pct) > 1e-6
        )
        if changed:
            self.state.current_levels = prop_levels
            self.state.current_band_pct = prop_band
            self.state.adjustments += 1
            action = f"adjust levels={prop_levels} band={prop_band:.4f}"
        else:
            action = "no_change"
        self.state.allowed += 1
        if self.cfg.emit_path:
            try:
                with open(self.cfg.emit_path, "a", encoding="utf-8") as f:
                    f.write(
                        json.dumps(
                            {
                                "action": action,
                                "score": score,
                                "levels": self.state.current_levels,
                                "band_pct": self.state.current_band_pct,
                                "ts": time.time(),
                            }
                        )
                        + "\n"
                    )
            except Exception as e:  # pragma: no cover
                log.error("emit failed %s", e)
        return action

    def learn(self, obs: Dict[str, Any], outcome: str) -> None:
        # Placeholder: could track realized PnL impact of parameter changes.
        return

    def run_once(self) -> Dict[str, Any]:
        self.state.cycles += 1
        obs = self.observe()
        score, meta = self.decide(obs)
        self.state.last_score = score
        action = self.act(obs, score, meta)
        self.state.last_action = action
        self.learn(obs, action)
        return {"score": score, "action": action, "state": asdict(self.state)}


def create_bot(**kwargs) -> AIGridControllerBot:
    return AIGridControllerBot(BotConfig(**kwargs))


def _selftest() -> int:
    bot = create_bot()
    r = bot.run_once()
    ok = 0.0 <= r["score"] <= 1.0 and "current_levels" in r["state"]
    print("AIGridControllerBot selftest", "PASS" if ok else "FAIL", json.dumps(r))
    return 0 if ok else 1


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--emit", type=str, default=None)
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    bot = create_bot(emit_path=args.emit)
    print(json.dumps(bot.run_once(), indent=2))
