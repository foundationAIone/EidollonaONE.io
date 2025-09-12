# trading_engine/margin_controller.py
# ===================================================================
# EidollonaONE Margin Controller — SE41 v4.1+ aligned
#
# What this module does
# - Computes required/maintenance margin & liquidation distance per account.
# - Reads SE41Signals each pass to raise/lower target equity buffers coherently.
# - Ethos gates risk-raising actions (borrow/increase leverage) before apply.
# - Enforces hard safety rails (maintenance %, LVR, max leverage).
# - Journals JSONL for a complete audit trail & replay.
# ===================================================================

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

# ---- SE41 v4.1 unified imports ------------------------------------
from symbolic_core.symbolic_equation41 import SymbolicEquation41
from trading.helpers.se41_trading_gate import se41_signals, ethos_decision, se41_numeric


# --------------------------- enums & dataclasses ---------------------------


class MarginAction(Enum):
    HOLD = "hold"
    RAISE_EQUITY_BUFFER = "raise_equity_buffer"
    REDUCE_EXPOSURE = "reduce_exposure"
    BORROW_MARGIN = "borrow_margin"
    PAYDOWN_MARGIN = "paydown_margin"
    PARTIAL_LIQUIDATION = "partial_liquidation"
    FULL_LIQUIDATION = "full_liquidation"


class MarginStatus(Enum):
    HEALTHY = "healthy"
    COMFORTABLE = "comfortable"
    WARNING = "warning"
    MARGIN_CALL = "margin_call"
    LIQUIDATION = "liquidation"


@dataclass
class MarginConfig:
    # Rail parameters
    initial_margin_req: float = 0.50  # 50% (portfolio-level proxy)
    maintenance_margin_req: float = 0.35
    max_leverage: float = 5.0  # 5x notional / equity
    liquidation_lvr: float = 0.90  # liquidate if LVR >= 90%

    # Dynamic buffers (adjusted via SE41)
    base_equity_buffer_pct: float = 0.05  # extra equity over maint req
    max_equity_buffer_pct: float = 0.20

    # Application dynamics
    adjust_speed: float = 0.35  # fraction of delta we apply per step
    min_partial_liq_notional: float = 1_000.0

    # Ethos gate for risk-raising moves (borrow / leverage increase)
    ethos_gate_risk_raising: bool = True

    # Journal path
    data_dir: str = "margin_data"


@dataclass
class MarginAccountSnapshot:
    account_id: str
    equity: float
    notional_long: float
    notional_short: float
    borrowed: float  # margin loan
    cash: float
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    # 1-day projected notional change (stress)
    stress_notional_up: float = 0.0
    stress_notional_dn: float = 0.0

    # Derived (helpful properties)
    @property
    def gross_notional(self) -> float:
        return max(0.0, self.notional_long + self.notional_short)

    @property
    def net_notional(self) -> float:
        return max(0.0, abs(self.notional_long - self.notional_short))

    @property
    def leverage(self) -> float:
        eq = max(self.equity, 1e-9)
        return self.gross_notional / eq

    @property
    def lvr(self) -> float:
        # Loan-to-Value ratio (approx): borrowed / (gross_notional or equity proxy)
        base = max(self.gross_notional, self.equity, 1e-9)
        return self.borrowed / base


@dataclass
class MarginTargets:
    target_equity_buffer: float  # absolute $ equity buffer to add (≥ 0)
    target_borrowed: float  # desired loan level (may be down)
    target_exposure: float  # desired gross notional (may be down)


@dataclass
class MarginRecommendation:
    recommendation_id: str
    action: MarginAction
    delta_equity: float = 0.0  # deposit/withdraw equity (positive = add equity)
    delta_borrowed: float = 0.0  # +borrow, −paydown
    reduce_notional_by: float = 0.0  # exposure reduction (liquidation or scale-down)
    confidence: float = 0.0
    reason: str = ""
    symbolic_strength: float = 0.0
    quantum_probability: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


# --------------------------- small helpers ---------------------------


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


# --------------------------- controller ---------------------------


class MarginController:
    """
    Margin Controller (SE41 v4.1+)
      • Computes required/maintenance margin & liquidation distance.
      • Raises/lowers target equity buffer coherently via SE41Signals.
      • Gates risk-raising moves by ETHOS; enforces rails: maint %, LVR, max leverage.
      • Journals all moves to JSONL for audit/replay.
    """

    def __init__(self, config: Optional[MarginConfig] = None):
        self.cfg = config or MarginConfig()
        self.logger = logging.getLogger(f"{__name__}.MarginController")
        self._se41 = SymbolicEquation41()
        self._dir = Path(self.cfg.data_dir)
        self._dir.mkdir(exist_ok=True)
        self._journal_path = self._dir / "margin_journal.jsonl"
        self._last_signals: Optional[Dict[str, Any]] = None
        self._last_targets: Optional[MarginTargets] = None

    # ---- compute

    def compute_requireds(self, snap: MarginAccountSnapshot) -> Dict[str, float]:
        """
        Compute initial/maintenance requirements, liquidation distance, and status rails.
        """
        # Proxies: portfolio-level requirements
        imr = self.cfg.initial_margin_req
        mmr = self.cfg.maintenance_margin_req
        gross = snap.gross_notional
        eq = max(snap.equity, 1e-9)

        # Required margin dollars
        initial_req = imr * gross
        maintenance_req = mmr * gross

        # Equity buffer above maintenance (≥ 0)
        equity_buffer = max(0.0, eq - maintenance_req)

        # Liquidation checks
        lvr = snap.lvr
        lev = snap.leverage

        # Distance to liquidation LVR (as fraction)
        dist_liq_lvr = max(0.0, self.cfg.liquidation_lvr - lvr)

        # Status classification
        if lvr >= self.cfg.liquidation_lvr or lev > self.cfg.max_leverage * 1.05:
            status = MarginStatus.LIQUIDATION
        elif eq < maintenance_req:
            status = MarginStatus.MARGIN_CALL
        elif (eq - maintenance_req) / max(maintenance_req, 1e-9) < 0.10:
            status = MarginStatus.WARNING
        elif (eq - maintenance_req) / max(maintenance_req, 1e-9) < 0.25:
            status = MarginStatus.COMFORTABLE
        else:
            status = MarginStatus.HEALTHY

        out = {
            "initial_req": initial_req,
            "maintenance_req": maintenance_req,
            "equity_buffer": equity_buffer,
            "dist_liq_lvr": dist_liq_lvr,
            "status": status.value,
            "lvr": lvr,
            "leverage": lev,
        }
        return out

    def compute_targets(
        self, snap: MarginAccountSnapshot, vol_proxy: float
    ) -> MarginTargets:
        """
        Compute target equity buffer / borrowed / exposure based on SE41Signals
        and rails (maintenance %, liquidation LVR, max leverage).
        """
        se = se41_signals() or {}
        self._last_signals = se

        # small numeric pulse to honor the SE41 rhythm (robust to failures)
        try:
            _ = se41_numeric(
                M_t=se.get("coherence", 0.5),
                DNA_states=[1.0, vol_proxy, snap.leverage, 1.1],
                harmonic_patterns=[1.0, 1.1, vol_proxy, min(snap.lvr, 1.0), 1.2],
            )
        except Exception:
            pass

        coh = float(se.get("coherence", 0.5))
        ethos = _ethos_min(se)
        risk = float(se.get("risk", 0.25))
        unc = float(se.get("uncertainty", 0.25))

        # Requireds & rails
        req = self.compute_requireds(snap)
        maint_req = req["maintenance_req"]
        eq = max(snap.equity, 1e-9)
        gross = snap.gross_notional

        # Equity buffer target (over maintenance), shaped by SE41
        base_buf_pct = self.cfg.base_equity_buffer_pct
        # Risk & uncertainty & vol increase target; coherence & ethos reduce need
        up = 0.40 * risk + 0.30 * unc + 0.30 * min(vol_proxy, 1.0)
        down = 0.25 * coh + 0.15 * ethos
        buf_pct = max(
            0.0, min(self.cfg.max_equity_buffer_pct, base_buf_pct + up - down)
        )
        target_buffer_abs = buf_pct * gross

        # Desired borrowed: lower if risk/unc high or coherence/ethos low
        # Start from current; push down when risk conditions deteriorate.
        desired_borrow = snap.borrowed
        desired_borrow *= (1.0 - 0.40 * max(risk + unc - 0.4, 0.0)) * (
            1.0 + 0.10 * max(coh + ethos - 1.2, 0.0)
        )
        desired_borrow = max(0.0, desired_borrow)

        # Desired exposure: cap using max leverage & liquidation LVR rail
        max_notional_by_leverage = self.cfg.max_leverage * eq
        desired_exposure = min(gross, max_notional_by_leverage)

        targets = MarginTargets(
            target_equity_buffer=target_buffer_abs,
            target_borrowed=desired_borrow,
            target_exposure=desired_exposure,
        )
        self._last_targets = targets
        return targets

    def recommend(
        self, snap: MarginAccountSnapshot, targets: MarginTargets
    ) -> MarginRecommendation:
        """
        Convert targets into an executable recommendation.
        """
        rid = f"margrec_{int(time.time())}"
        req = self.compute_requireds(snap)
        maint_req = req["maintenance_req"]

        # equity buffer shortfall
        current_buffer = max(0.0, snap.equity - maint_req)
        delta_buffer = targets.target_equity_buffer - current_buffer

        # Borrow & exposure deltas
        delta_borrow = targets.target_borrowed - snap.borrowed
        reduce_expo = max(0.0, snap.gross_notional - targets.target_exposure)

        # Choose primary action
        if req["status"] in (MarginStatus.LIQUIDATION.value,):
            act = MarginAction.FULL_LIQUIDATION
            reason = "rail_liquidation_trigger"
        elif req["status"] in (MarginStatus.MARGIN_CALL.value,):
            # margin call → raise equity buffer or reduce exposure
            if delta_buffer > 0:
                act = MarginAction.RAISE_EQUITY_BUFFER
                reason = "margin_call_raise_buffer"
            else:
                act = MarginAction.REDUCE_EXPOSURE
                reason = "margin_call_reduce_exposure"
        else:
            # healthy-ish → move gradually toward targets
            if delta_buffer > 0.0:
                act = MarginAction.RAISE_EQUITY_BUFFER
                reason = "increase_buffer_to_target"
            elif reduce_expo > self.cfg.min_partial_liq_notional:
                act = MarginAction.REDUCE_EXPOSURE
                reason = "scale_down_to_target"
            elif delta_borrow < 0:
                act = MarginAction.PAYDOWN_MARGIN
                reason = "paydown_toward_target"
            elif delta_borrow > 0:
                act = MarginAction.BORROW_MARGIN
                reason = "borrow_toward_target"
            else:
                act = MarginAction.HOLD
                reason = "at_target"

        # Confidence from SE41 (bounded)
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

        # Symbolic/quantum spice
        try:
            num = se41_numeric(
                DNA_states=[1.0, conf, snap.leverage, 1.1],
                harmonic_patterns=[1.0, 1.1, conf, min(snap.lvr, 1.0), 1.2],
            )
            sym = max(0.0, min(1.0, abs(float(num)) / 50.0))
        except Exception:
            sym = conf
        qp = min(1.0, conf * (0.95 + 0.1 * random.random()))

        # Prepare magnitudes (partial-step)
        deq = max(0.0, self.cfg.adjust_speed * delta_buffer)
        dbw = self.cfg.adjust_speed * delta_borrow
        dex = self.cfg.adjust_speed * reduce_expo

        rec = MarginRecommendation(
            recommendation_id=rid,
            action=act,
            delta_equity=deq,
            delta_borrowed=dbw,
            reduce_notional_by=dex,
            confidence=conf,
            reason=reason,
            symbolic_strength=sym,
            quantum_probability=qp,
        )
        return rec

    def apply(
        self, snap: MarginAccountSnapshot, rec: MarginRecommendation
    ) -> Dict[str, Any]:
        """
        Apply a recommendation with rail checks and ethos gating for risk-raising moves.
        Returns an outcome dict with post-state preview.
        """
        se = self._last_signals or {}
        result = {"applied": False, "reason": "noop"}

        # Gate risk-raising moves (borrow / leverage up)
        if self.cfg.ethos_gate_risk_raising and rec.action in (
            MarginAction.BORROW_MARGIN,
        ):
            amount = abs(rec.delta_borrowed)
            allow, why = ethos_decision(
                {
                    "id": rec.recommendation_id,
                    "purpose": "margin_borrow",
                    "amount": float(amount),
                    "currency": "NOM",
                    "tags": ["margin", "borrow", "risk_raise"],
                }
            )
            if allow == "deny":
                self._journal(
                    {
                        "type": "ethos_deny",
                        "rec": _rec_dict(rec),
                        "reason": why,
                        "snap": _snap_dict(snap),
                        "se41": _se_brief(se),
                        "ts": _now(),
                    }
                )
                result.update({"applied": False, "reason": f"ethos_deny:{why}"})
                return result

        # Project state after partial step
        post = _projected_snapshot(self.cfg, snap, rec)

        # Recompute rails post-action
        rails = self.compute_requireds(post)

        # Hard rails: leverage, LVR, maintenance margin
        if rails["leverage"] > self.cfg.max_leverage * 1.001:
            self._journal(
                {
                    "type": "rail_block_leverage",
                    "post": rails,
                    "rec": _rec_dict(rec),
                    "ts": _now(),
                }
            )
            return {"applied": False, "reason": "max_leverage"}
        if rails["lvr"] >= self.cfg.liquidation_lvr:
            self._journal(
                {
                    "type": "rail_block_lvr",
                    "post": rails,
                    "rec": _rec_dict(rec),
                    "ts": _now(),
                }
            )
            return {"applied": False, "reason": "liquidation_lvr"}
        if rails["status"] in (
            MarginStatus.MARGIN_CALL.value,
            MarginStatus.LIQUIDATION.value,
        ):
            self._journal(
                {
                    "type": "rail_block_maint",
                    "post": rails,
                    "rec": _rec_dict(rec),
                    "ts": _now(),
                }
            )
            return {"applied": False, "reason": "maintenance_req"}

        # Commit partial step (in real engine you would call broker/executor here)
        deltas = {
            "equity_applied": post.equity - snap.equity,
            "borrow_applied": post.borrowed - snap.borrowed,
            "notional_reduced": (snap.gross_notional - post.gross_notional),
        }

        self._journal(
            {
                "type": "apply",
                "rec": _rec_dict(rec),
                "pre": _snap_dict(snap),
                "post": _snap_dict(post),
                "se41": _se_brief(se),
                "deltas": deltas,
                "ts": _now(),
            }
        )

        result.update({"applied": True, "post": _snap_dict(post), "deltas": deltas})
        return result

    # ---- internal

    def _journal(self, obj: Dict[str, Any]) -> None:
        try:
            with self._journal_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(obj) + "\n")
        except Exception:
            pass


# --------------------------- utilities ---------------------------


def _now() -> str:
    return datetime.now().isoformat()


def _projected_snapshot(
    cfg: MarginConfig, snap: MarginAccountSnapshot, rec: MarginRecommendation
) -> MarginAccountSnapshot:
    """
    Simulate a partial step toward targets:
      +equity (deposit), +/−borrowed, reduce gross notional by some amount.
    For simplicity we reduce long & short proportionally to preserve net where feasible.
    """
    eq = max(0.0, snap.equity + rec.delta_equity)
    brw = max(0.0, snap.borrowed + rec.delta_borrowed)
    long = snap.notional_long
    shrt = snap.notional_short
    gross = snap.gross_notional

    reduce_amt = min(rec.reduce_notional_by, gross)
    if reduce_amt > 0:
        # proportional scale down
        w_long = long / gross if gross > 0 else 0.5
        long = max(0.0, long - reduce_amt * w_long)
        shrt = max(0.0, shrt - reduce_amt * (1.0 - w_long))

    # keep cash proxy: equity = cash + longs - shorts - borrowed (approx)
    # Solve for cash: cash_new = eq_new - (long - short) + borrowed
    net = long - shrt
    cash_new = eq - net + brw

    post = MarginAccountSnapshot(
        account_id=snap.account_id,
        equity=eq,
        notional_long=long,
        notional_short=shrt,
        borrowed=brw,
        cash=cash_new,
        realized_pnl=snap.realized_pnl,
        unrealized_pnl=snap.unrealized_pnl,
        stress_notional_up=snap.stress_notional_up,
        stress_notional_dn=snap.stress_notional_dn,
    )
    return post


def _rec_dict(rec: MarginRecommendation) -> Dict[str, Any]:
    return {
        "id": rec.recommendation_id,
        "action": rec.action.value,
        "delta_equity": rec.delta_equity,
        "delta_borrowed": rec.delta_borrowed,
        "reduce_notional_by": rec.reduce_notional_by,
        "confidence": rec.confidence,
        "reason": rec.reason,
        "symbolic_strength": rec.symbolic_strength,
        "quantum_probability": rec.quantum_probability,
        "ts": rec.timestamp.isoformat(),
    }


def _snap_dict(s: MarginAccountSnapshot) -> Dict[str, Any]:
    return {
        "account_id": s.account_id,
        "equity": s.equity,
        "notional_long": s.notional_long,
        "notional_short": s.notional_short,
        "gross_notional": s.gross_notional,
        "borrowed": s.borrowed,
        "cash": s.cash,
        "leverage": s.leverage,
        "lvr": s.lvr,
        "stress_up": s.stress_notional_up,
        "stress_dn": s.stress_notional_dn,
    }


# --------------------------- factory & smoke ---------------------------


def create_margin_controller(**kwargs) -> MarginController:
    return MarginController(**kwargs)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    print("=" * 74)
    print("EidollonaONE Margin Controller v4.1+ — coherent • ethical • resilient")
    print("=" * 74)

    ctrl = create_margin_controller()

    snap = MarginAccountSnapshot(
        account_id="acct_001",
        equity=120_000.0,
        notional_long=240_000.0,
        notional_short=40_000.0,
        borrowed=60_000.0,
        cash=20_000.0,
        stress_notional_up=30_000.0,
        stress_notional_dn=45_000.0,
    )

    req = ctrl.compute_requireds(snap)
    print("Requireds:", json.dumps(req, indent=2))

    targets = ctrl.compute_targets(snap, vol_proxy=0.25)
    print(
        "Targets:",
        json.dumps(
            {
                "equity_buffer": targets.target_equity_buffer,
                "borrowed": targets.target_borrowed,
                "exposure": targets.target_exposure,
            },
            indent=2,
        ),
    )

    rec = ctrl.recommend(snap, targets)
    print("Recommendation:", json.dumps(_rec_dict(rec), indent=2))

    out = ctrl.apply(snap, rec)
    print("Apply:", json.dumps(out, indent=2))

__all__ = [
    "MarginController",
    "create_margin_controller",
    "MarginConfig",
    "MarginAccountSnapshot",
    "MarginTargets",
    "MarginRecommendation",
]
