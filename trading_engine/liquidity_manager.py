"""trading_engine.liquidity_manager
============================================================
SE41 v4.1+ Liquidity Manager

Key Features
------------
1. Unified Signal Intake: Pulls fresh SE41Signals every cycle (se41_signals()).
2. Bounded Target Derivation:
   Cash / stable / credit usage derived via symbolic-bounded formulas:
    - Rewards: coherence, mirror_consistency, ethos (minimum pillar)
    - Dampers: risk, uncertainty, volatility, projected net outflows
3. Ethos Gating:
   Any reduction of defensive buffers (deploy cash, reduce stables, open credit) is gated.
4. Safety Rails:
    - Minimum cash percent
    - LCR (Liquidity Coverage Ratio) minimum + warn bias
    - Credit utilization cap
5. Gradual Adjustment: Fractional progress toward targets each apply() to avoid shocks.
6. Structured Recommendations: compute_targets() -> recommend() -> apply() separation.
7. JSONL Journaling: Every recommendation application & rail block is appended for audit / replay.

The manager purposely remains self-contained (no external DB writes) and side‑effect minimal,
focusing on deterministic calculations + append‑only journaling.
"""

from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Any

from symbolic_core.symbolic_equation41 import SymbolicEquation41
from trading.helpers.se41_trading_gate import se41_signals, ethos_decision, se41_numeric


# ---------------------------------------------------------------------------
# Enums & Dataclasses
# ---------------------------------------------------------------------------


class LiquidityAction(Enum):
    HOLD = "hold"
    INCREASE_CASH = "increase_cash"
    DEPLOY_CASH = "deploy_cash"
    RAISE_STABLE = "raise_stable_liquidity"
    REDUCE_STABLE = "reduce_stable_liquidity"
    OPEN_CREDIT = "open_credit"
    PAYDOWN_CREDIT = "paydown_credit"
    REALLOCATE_INTERNAL = "reallocate_internal"


@dataclass
class LiquidityConfig:
    # Target structure (% of total portfolio value)
    min_cash_pct: float = 0.07  # Hard floor
    base_cash_pct: float = 0.10
    max_cash_pct: float = 0.35

    base_stable_pct: float = 0.15  # Short-duration / near-cash
    max_stable_pct: float = 0.50

    # Credit
    credit_limit_pct: float = 0.20  # Implied vs equity (informational)
    max_credit_util_pct: float = 0.40  # Cap of limit

    # Liquidity Coverage Ratio rails (HQLA / net cash out 30d)
    lcr_min: float = 1.10
    lcr_warn: float = 1.25

    # Dynamics
    adjust_speed: float = 0.25  # Fraction of gap applied per cycle
    rebal_threshold: float = 0.15  # Unused placeholder for potential rebalance logic
    deploy_ethos_gate: bool = True  # Gate outward / risk‑adding moves


@dataclass
class LiquiditySnapshot:
    total_value: float = 0.0
    cash_value: float = 0.0
    stable_value: float = 0.0
    credit_limit: float = 0.0
    credit_used: float = 0.0
    net_cash_out_30d: float = 0.0  # Positive = net outflow

    @property
    def cash_pct(self) -> float:
        return 0.0 if self.total_value <= 0 else self.cash_value / self.total_value

    @property
    def stable_pct(self) -> float:
        return 0.0 if self.total_value <= 0 else self.stable_value / self.total_value

    @property
    def credit_util_pct(self) -> float:
        return 0.0 if self.credit_limit <= 0 else self.credit_used / self.credit_limit

    @property
    def hqla(self) -> float:
        return self.cash_value + 0.85 * self.stable_value

    @property
    def lcr(self) -> float:
        out = max(self.net_cash_out_30d, 0.0)
        return float("inf") if out == 0 else self.hqla / out


@dataclass
class LiquidityTargets:
    target_cash_value: float
    target_stable_value: float
    target_credit_used: float


@dataclass
class LiquidityRecommendation:
    recommendation_id: str
    action: LiquidityAction
    delta_cash: float = 0.0
    delta_stable: float = 0.0
    delta_credit: float = 0.0
    confidence: float = 0.0
    reason: str = ""
    symbolic_strength: float = 0.0
    quantum_probability: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _ethos_min(sig: Dict[str, Any]) -> float:
    e = sig.get("ethos", {}) if isinstance(sig, dict) else {}
    if not e:
        return 0.0
    return min(
        float(e.get("authenticity", 0.0)),
        float(e.get("integrity", 0.0)),
        float(e.get("responsibility", 0.0)),
        float(e.get("enrichment", 0.0)),
    )


def _bounded_cash_pct_from_se41(
    cfg: LiquidityConfig, se: Dict[str, Any], vol: float, net_out_30d: float, tv: float
) -> float:
    if tv <= 0:
        return cfg.base_cash_pct
    coh = float(se.get("coherence", 0.5))
    ethos = _ethos_min(se)
    risk = float(se.get("risk", 0.25))
    unc = float(se.get("uncertainty", 0.25))
    mc = float(se.get("mirror_consistency", 0.5))
    out_ratio = max(net_out_30d, 0.0) / max(tv, 1e-9)

    up = (
        0.10
        + 0.40 * risk
        + 0.25 * unc
        + 0.25 * min(vol, 1.0)
        + 0.30 * min(out_ratio, 0.6)
    )
    down = 0.20 * coh + 0.15 * ethos + 0.05 * mc
    raw = cfg.base_cash_pct + up - down
    return max(cfg.min_cash_pct, min(cfg.max_cash_pct, raw))


def _bounded_stable_pct_from_se41(
    cfg: LiquidityConfig, se: Dict[str, Any], vol: float
) -> float:
    coh = float(se.get("coherence", 0.5))
    ethos = _ethos_min(se)
    risk = float(se.get("risk", 0.25))
    unc = float(se.get("uncertainty", 0.25))
    raw = (
        cfg.base_stable_pct
        + 0.30 * min(vol, 1.0)
        + 0.20 * risk
        + 0.10 * unc
        - 0.20 * coh
        - 0.10 * ethos
    )
    return max(0.05, min(cfg.max_stable_pct, raw))


def _bounded_credit_used_from_se41(
    cfg: LiquidityConfig, se: Dict[str, Any], snap: LiquiditySnapshot
) -> float:
    limit = snap.credit_limit
    if limit <= 0:
        return 0.0
    coh = float(se.get("coherence", 0.5))
    risk = float(se.get("risk", 0.25))
    unc = float(se.get("uncertainty", 0.25))
    eth = _ethos_min(se)

    base = 0.10 * limit
    bonus = max(0.0, (coh + eth - 0.8)) * 0.25 * limit
    malus = max(0.0, (risk + unc - 0.3)) * 0.30 * limit
    target = base + bonus - malus
    max_used = cfg.max_credit_util_pct * limit
    return max(0.0, min(max_used, target))


# ---------------------------------------------------------------------------
# Liquidity Manager
# ---------------------------------------------------------------------------


class LiquidityManager:
    """SE41-aligned Liquidity Manager (cash / stables / credit rails)."""

    def __init__(
        self, config: Optional[LiquidityConfig] = None, data_dir: Optional[str] = None
    ):
        self.logger = logging.getLogger(f"{__name__}.LiquidityManager")
        self.cfg = config or LiquidityConfig()
        self._se41 = SymbolicEquation41()
        self._dir = Path(data_dir or "liquidity_data")
        self._dir.mkdir(exist_ok=True)
        self._journal_path = self._dir / "liquidity_journal.jsonl"
        self._last_targets: Optional[LiquidityTargets] = None
        self._last_signals: Optional[Dict[str, Any]] = None

    def compute_targets(
        self, snap: LiquiditySnapshot, market_vol: float
    ) -> LiquidityTargets:
        se = se41_signals() or {}
        self._last_signals = se
        try:
            _ = se41_numeric(
                M_t=se.get("coherence", 0.5),
                DNA_states=[1.0, market_vol, snap.lcr, 1.1],
                harmonic_patterns=[
                    1.0,
                    1.1,
                    market_vol,
                    min(snap.credit_util_pct, 1.0),
                    1.2,
                ],
            )
        except Exception:
            pass

        cash_pct = _bounded_cash_pct_from_se41(
            self.cfg, se, market_vol, snap.net_cash_out_30d, snap.total_value
        )
        stable_pct = _bounded_stable_pct_from_se41(self.cfg, se, market_vol)
        credit_used = _bounded_credit_used_from_se41(self.cfg, se, snap)

        cash_abs = cash_pct * snap.total_value
        stable_abs = stable_pct * snap.total_value
        credit_abs = credit_used

        if snap.lcr < self.cfg.lcr_min:
            deficit = (self.cfg.lcr_min * max(snap.net_cash_out_30d, 0.0)) - snap.hqla
            cash_abs += max(0.0, deficit)
        elif snap.lcr < self.cfg.lcr_warn:
            bias = (
                0.15 * (self.cfg.lcr_warn - snap.lcr) * max(snap.net_cash_out_30d, 0.0)
            )
            cash_abs += max(0.0, bias)

        if snap.credit_util_pct >= self.cfg.max_credit_util_pct:
            credit_abs = min(credit_abs, snap.credit_used)

        targets = LiquidityTargets(
            target_cash_value=max(0.0, cash_abs),
            target_stable_value=max(0.0, stable_abs),
            target_credit_used=max(0.0, credit_abs),
        )
        self._last_targets = targets
        return targets

    def recommend(
        self, snap: LiquiditySnapshot, targets: LiquidityTargets
    ) -> LiquidityRecommendation:
        rid = f"liqrec_{int(time.time())}"
        dcash = targets.target_cash_value - snap.cash_value
        dstable = targets.target_stable_value - snap.stable_value
        dcredit = targets.target_credit_used - snap.credit_used

        if dcash > 0:
            act = LiquidityAction.INCREASE_CASH
            reason = "raise_cash_to_target"
        elif dcash < 0:
            act = LiquidityAction.DEPLOY_CASH
            reason = "deploy_cash_excess"
        elif dstable > 0:
            act = LiquidityAction.RAISE_STABLE
            reason = "raise_stable_to_target"
        elif dstable < 0:
            act = LiquidityAction.REDUCE_STABLE
            reason = "reduce_stable_excess"
        elif dcredit > 0:
            act = LiquidityAction.OPEN_CREDIT
            reason = "open_credit_to_target"
        elif dcredit < 0:
            act = LiquidityAction.PAYDOWN_CREDIT
            reason = "paydown_credit"
        else:
            act = LiquidityAction.HOLD
            reason = "at_target"

        se = self._last_signals or {}
        conf = max(
            0.0,
            min(
                1.0,
                0.45 * float(se.get("coherence", 0.5))
                + 0.25 * _ethos_min(se)
                - 0.20 * float(se.get("risk", 0.25))
                - 0.10 * float(se.get("uncertainty", 0.25)),
            ),
        )
        try:
            num = se41_numeric(
                DNA_states=[1.0, conf, snap.lcr, 1.1],
                harmonic_patterns=[1.0, 1.1, conf, min(snap.credit_util_pct, 1.0), 1.2],
            )
            sym = max(0.0, min(1.0, abs(float(num)) / 50.0))
        except Exception:
            sym = conf
        qp = min(1.0, conf * (0.95 + 0.1 * random.random()))

        return LiquidityRecommendation(
            recommendation_id=rid,
            action=act,
            delta_cash=dcash,
            delta_stable=dstable,
            delta_credit=dcredit,
            confidence=conf,
            reason=reason,
            symbolic_strength=sym,
            quantum_probability=qp,
        )

    def apply(
        self, snap: LiquiditySnapshot, rec: LiquidityRecommendation
    ) -> Dict[str, Any]:
        se = self._last_signals or {}

        def _projected(
            s: LiquiditySnapshot, dc: float, ds: float, dcr: float
        ) -> LiquiditySnapshot:
            p = LiquiditySnapshot(**s.__dict__)
            p.cash_value = max(0.0, p.cash_value + self.cfg.adjust_speed * dc)
            p.stable_value = max(0.0, p.stable_value + self.cfg.adjust_speed * ds)
            p.credit_used = max(
                0.0, min(p.credit_limit, p.credit_used + self.cfg.adjust_speed * dcr)
            )
            return p

        if self.cfg.deploy_ethos_gate and rec.action in (
            LiquidityAction.DEPLOY_CASH,
            LiquidityAction.REDUCE_STABLE,
            LiquidityAction.OPEN_CREDIT,
        ):
            deploy_value = abs(
                rec.delta_cash
                if rec.action == LiquidityAction.DEPLOY_CASH
                else (
                    rec.delta_stable
                    if rec.action == LiquidityAction.REDUCE_STABLE
                    else rec.delta_credit
                )
            )
            allow, reason = ethos_decision(
                {
                    "id": rec.recommendation_id,
                    "purpose": "liquidity_deployment",
                    "amount": float(deploy_value),
                    "currency": "NOM",
                    "tags": ["liquidity", "deployment", "buffers"],
                }
            )
            if allow == "deny":
                self._journal(
                    {
                        "type": "ethos_deny",
                        "rec": _rec_dict(rec),
                        "reason": reason,
                        "ts": datetime.now().isoformat(),
                    }
                )
                return {"applied": False, "reason": f"ethos_deny:{reason}"}

        proj = _projected(snap, rec.delta_cash, rec.delta_stable, rec.delta_credit)
        if proj.total_value > 0 and proj.cash_pct < self.cfg.min_cash_pct:
            self._journal(
                {
                    "type": "rail_block_min_cash",
                    "rec": _rec_dict(rec),
                    "post_cash_pct": proj.cash_pct,
                    "ts": datetime.now().isoformat(),
                }
            )
            return {"applied": False, "reason": "min_cash_floor"}
        if proj.lcr < self.cfg.lcr_min:
            self._journal(
                {
                    "type": "rail_block_lcr",
                    "rec": _rec_dict(rec),
                    "post_lcr": proj.lcr,
                    "ts": datetime.now().isoformat(),
                }
            )
            return {"applied": False, "reason": "lcr_min"}
        if proj.credit_util_pct > self.cfg.max_credit_util_pct:
            self._journal(
                {
                    "type": "rail_block_credit_util",
                    "rec": _rec_dict(rec),
                    "post_util": proj.credit_util_pct,
                    "ts": datetime.now().isoformat(),
                }
            )
            return {"applied": False, "reason": "credit_util_cap"}

        applied = {
            "cash_applied": proj.cash_value - snap.cash_value,
            "stable_applied": proj.stable_value - snap.stable_value,
            "credit_applied": proj.credit_used - snap.credit_used,
        }
        self._journal(
            {
                "type": "apply",
                "rec": _rec_dict(rec),
                "applied": applied,
                "se41": _se_brief(se),
                "post": _snap_dict(proj),
                "ts": datetime.now().isoformat(),
            }
        )
        return {"applied": True, "applied_step": applied, "post": _snap_dict(proj)}

    def _journal(self, obj: Dict[str, Any]) -> None:
        try:
            with self._journal_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(obj) + "\n")
        except Exception:
            pass


def _rec_dict(rec: LiquidityRecommendation) -> Dict[str, Any]:
    return {
        "id": rec.recommendation_id,
        "action": rec.action.value,
        "delta_cash": rec.delta_cash,
        "delta_stable": rec.delta_stable,
        "delta_credit": rec.delta_credit,
        "confidence": rec.confidence,
        "reason": rec.reason,
        "symbolic_strength": rec.symbolic_strength,
        "quantum_probability": rec.quantum_probability,
        "ts": rec.timestamp.isoformat(),
    }


def _snap_dict(s: LiquiditySnapshot) -> Dict[str, Any]:
    return {
        "total_value": s.total_value,
        "cash_value": s.cash_value,
        "stable_value": s.stable_value,
        "credit_limit": s.credit_limit,
        "credit_used": s.credit_used,
        "cash_pct": s.cash_pct,
        "stable_pct": s.stable_pct,
        "credit_util_pct": s.credit_util_pct,
        "net_cash_out_30d": s.net_cash_out_30d,
        "hqla": s.hqla,
        "lcr": s.lcr,
    }


def _se_brief(se: Dict[str, Any]) -> Dict[str, Any]:
    if not se:
        return {}
    return {
        "coherence": se.get("coherence", 0.0),
        "risk": se.get("risk", 0.0),
        "uncertainty": se.get("uncertainty", 0.0),
        "mirror_consistency": se.get("mirror_consistency", 0.0),
        "ethos_min": _ethos_min(se),
    }


def create_liquidity_manager(**kwargs) -> LiquidityManager:
    return LiquidityManager(**kwargs)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    print("=" * 70)
    print("EidollonaONE Liquidity Manager v4.1+ — coherent • ethical • resilient")
    print("=" * 70)
    mgr = create_liquidity_manager()
    snap = LiquiditySnapshot(
        total_value=250_000.0,
        cash_value=22_000.0,
        stable_value=35_000.0,
        credit_limit=50_000.0,
        credit_used=5_000.0,
        net_cash_out_30d=18_000.0,
    )
    market_vol = 0.22
    targets = mgr.compute_targets(snap, market_vol)
    rec = mgr.recommend(snap, targets)
    out = mgr.apply(snap, rec)
    print(
        json.dumps(
            {
                "targets": {
                    "cash": targets.target_cash_value,
                    "stable": targets.target_stable_value,
                    "credit_used": targets.target_credit_used,
                },
                "recommendation": _rec_dict(rec),
                "apply_result": out,
            },
            indent=2,
        )
    )


if __name__ == "__main__":  # pragma: no cover
    main()

__all__ = [
    "LiquidityManager",
    "create_liquidity_manager",
    "LiquidityConfig",
    "LiquiditySnapshot",
    "LiquidityTargets",
    "LiquidityRecommendation",
]
