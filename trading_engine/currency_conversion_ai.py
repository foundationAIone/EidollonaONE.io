# trading_engine/currency_conversion_ai.py
# ============================================================
# EidollonaONE Currency Conversion AI — SE41 v4.1+ aligned
# - Reads SE41Signals via trading.helpers.se41_trading_gate.se41_signals()
# - Computes symbolic coherence for FX operations (coherence + mirror + ethos)
#   damped by risk/uncertainty
# - Ethos-gates large or sensitive transfers (ethos_decision)
# - Provides quote/route/convert API with audit metadata
# ============================================================

from __future__ import annotations

import logging
import math
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any

# v4.1 (kept for optional local evaluation fallback)
from symbolic_core.symbolic_equation41 import SymbolicEquation41
from symbolic_core.context_builder import assemble_se41_context

# Shared, centralized SE41 trading helpers
from trading.helpers.se41_trading_gate import se41_signals, ethos_decision


# ----------------------------- Utilities & Enums -----------------------------

FX = str  # currency code alias (e.g., 'USD', 'EUR', 'BTC')


class LiquidityTier(Enum):
    TOP = "top"  # G10, BTC/USDT etc.
    MID = "mid"  # majors vs minors, liquid alts
    LONG_TAIL = "long"  # exotics, illiquid tokens


class RouteQuality(Enum):
    DIRECT = "direct"
    MULTIHOP = "multihop"
    SYNTH = "synthetic"


@dataclass
class FXQuote:
    request_id: str
    base: FX
    quote: FX
    amount_base: float
    rate: float  # base→quote rate
    spread_bps: float
    est_slippage_bps: float
    fees_quote: float
    route: RouteQuality
    route_path: List[FX]
    symbolic_coherence: float
    ts: datetime = field(default_factory=datetime.now)

    @property
    def amount_quote(self) -> float:
        return round(self.amount_base * self.rate, 8)


@dataclass
class ConversionRequest:
    req_id: str
    src: FX
    dst: FX
    amount_src: float
    purpose: str = "general_fx"
    client_id: Optional[str] = None
    urgency: float = 0.5  # 0..1
    allow_multihop: bool = True
    max_spread_bps: Optional[float] = None
    tags: List[str] = field(default_factory=lambda: ["fx", "conversion"])


@dataclass
class ConversionResult:
    conversion_id: str
    request_id: str
    src: FX
    dst: FX
    amount_src: float
    amount_dst: float
    exec_rate: float
    route: RouteQuality
    route_path: List[FX]
    fees_dst: float
    symbolic_coherence: float
    ethos_decision: str
    ethos_reason: str
    ts: datetime = field(default_factory=datetime.now)


# ----------------------------- v4.1 Signal Math -----------------------------


def _min_ethos(sig: Dict[str, Any]) -> float:
    e = sig.get("ethos", {})
    if not isinstance(e, dict) or not e:
        return 0.0
    return min(
        float(e.get("authenticity", 0.0)),
        float(e.get("integrity", 0.0)),
        float(e.get("responsibility", 0.0)),
        float(e.get("enrichment", 0.0)),
    )


def _symbolic_coherence(sig: Dict[str, Any]) -> float:
    """
    Bounded coherence scalar [0..1] for FX:
    blend of coherence + mirror_consistency + ethos_min, damped by risk + uncertainty.
    """
    if not sig:
        return 0.0
    coh = float(sig.get("coherence", 0.0))
    mc = float(sig.get("mirror_consistency", 0.0))
    me = _min_ethos(sig)
    risk = float(sig.get("risk", 0.2))
    unc = float(sig.get("uncertainty", 0.2))
    raw = 0.55 * coh + 0.25 * mc + 0.20 * me
    damp = max(0.35, 1.0 - 0.50 * (risk + unc))
    return max(0.0, min(1.0, raw * damp))


# ----------------------------- Mock Rate Provider (pluggable) -----------------------------


class FXRateProvider:
    """
    Replace this with adapters to live FX/crypto APIs.
    Here we simulate rates/spreads by tier and time-of-day.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.FXRateProvider")

    def _tier(self, a: FX, b: FX) -> LiquidityTier:
        majors = {"USD", "EUR", "JPY", "GBP", "CHF", "AUD", "CAD", "NZD"}
        if a in majors and b in majors:
            return LiquidityTier.TOP
        if a in {"BTC", "ETH", "USDT"} or b in {"BTC", "ETH", "USDT"}:
            return LiquidityTier.TOP
        if a in majors or b in majors:
            return LiquidityTier.MID
        return LiquidityTier.LONG_TAIL

    def _base_rate(self, a: FX, b: FX) -> float:
        # Toy matrix: anchor to USD then cross, or to BTC for crypto pairs
        if a == b:
            return 1.0
        anchors = {
            "USD": 1.0,
            "EUR": 1.08,
            "JPY": 0.0063,
            "GBP": 1.26,
            "CHF": 1.12,
            "AUD": 0.67,
            "CAD": 0.73,
            "NZD": 0.61,
            "BTC": 65000.0,
            "ETH": 3200.0,
            "USDT": 1.0,
        }
        ax = anchors.get(a, 0.5)
        bx = anchors.get(b, 0.5)
        rate = (ax / bx) if bx > 0 else 0.0
        # micro drift
        return max(1e-9, rate * (1.0 + random.uniform(-0.002, 0.002)))

    def _spread_bps(self, tier: LiquidityTier, amount: float) -> float:
        base = {
            LiquidityTier.TOP: 4.0,
            LiquidityTier.MID: 15.0,
            LiquidityTier.LONG_TAIL: 45.0,
        }[tier]
        size_penalty = min(60.0, math.log10(max(1.0, amount)) * 4.0)
        return base + size_penalty

    def _slippage_bps(self, tier: LiquidityTier, urgency: float) -> float:
        return {
            LiquidityTier.TOP: 2.0,
            LiquidityTier.MID: 10.0,
            LiquidityTier.LONG_TAIL: 35.0,
        }[tier] * (0.5 + urgency)

    def _fees(self, dst_amount: float, tier: LiquidityTier) -> float:
        # flat + variable (illustrative)
        flat = {
            LiquidityTier.TOP: 0.50,
            LiquidityTier.MID: 1.25,
            LiquidityTier.LONG_TAIL: 3.00,
        }[tier]
        variable = (
            dst_amount
            * {
                LiquidityTier.TOP: 0.0002,
                LiquidityTier.MID: 0.0005,
                LiquidityTier.LONG_TAIL: 0.001,
            }[tier]
        )
        return round(flat + variable, 4)

    def direct_quote(
        self, base: FX, quote: FX, amount_base: float, urgency: float
    ) -> Tuple[float, float, float, float]:
        tier = self._tier(base, quote)
        rate = self._base_rate(base, quote)
        spread_bps = self._spread_bps(tier, amount_base)
        slippage_bps = self._slippage_bps(tier, urgency)
        fees_quote = self._fees(amount_base * rate, tier)
        # effective rate after spread/est. slippage (bps → decimal)
        eff = rate * (1.0 - (spread_bps + slippage_bps) / 10_000.0)
        return eff, spread_bps, slippage_bps, fees_quote

    def multihop_quote(
        self, base: FX, quote: FX, amount_base: float, urgency: float
    ) -> Tuple[float, float, float, float, List[FX]]:
        """
        Simple 2-hop via USD or USDT to model routing improvements.
        """
        hops: List[FX] = []
        pivot = "USD" if {"USD", base, quote} else "USDT"

        # hop1: base->pivot
        r1, s1, l1, f1 = self.direct_quote(base, pivot, amount_base, urgency)
        amt1 = amount_base * r1

        # hop2: pivot->quote
        r2, s2, l2, f2 = self.direct_quote(pivot, quote, amt1, urgency)

        # Combine as geometric composition with bps aggregated
        eff = r2  # amt1 already includes hop1
        spread_bps = s1 + s2 - 3.0  # small synergy discount
        slippage_bps = l1 + l2 - 2.0
        fees_quote = f1 + f2

        hops = [base, pivot, quote]
        return eff, max(0.0, spread_bps), max(0.0, slippage_bps), fees_quote, hops


# ----------------------------- Currency Conversion AI -----------------------------


class CurrencyConversionAI:
    """
    Currency Conversion AI — SE41 v4.1+
    - Quotes, routes (direct/multihop), converts with fees/est. slippage
    - Symbolic (SE41) coherence per request
    - Ethos-gated large/sensitive transfers
    """

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self.logger = logging.getLogger(f"{__name__}.CurrencyConversionAI")
        self.data_dir = Path(data_dir or "currency_conversion_data")
        self.data_dir.mkdir(exist_ok=True)
        self.rate_provider = FXRateProvider()
        self._se41 = SymbolicEquation41()  # for local fallback only

        # Policy knobs
        self.large_transfer_threshold = 250_000.0  # in src currency nominal
        self.max_spread_bps_default = 120.0

    # ----------------- Public API -----------------

    def quote(self, req: ConversionRequest) -> FXQuote:
        """
        Produce a priceable quote for req. Uses direct or multihop depending on liquidity and flag.
        """
        sig = self._signals()
        coh = _symbolic_coherence(sig)

        # Cheapest of (direct, multihop) if allowed
        direct = self.rate_provider.direct_quote(
            req.src, req.dst, req.amount_src, req.urgency
        )
        eff_d, sp_d, slip_d, fee_d = direct
        best_eff, best_sp, best_slip, best_fee, best_route, best_path = (
            eff_d,
            sp_d,
            slip_d,
            fee_d,
            RouteQuality.DIRECT,
            [req.src, req.dst],
        )

        if req.allow_multihop:
            mh_eff, mh_sp, mh_slip, mh_fee, mh_path = self.rate_provider.multihop_quote(
                req.src, req.dst, req.amount_src, req.urgency
            )
            # Prefer route with higher final dst amount (eff rate)
            if (req.amount_src * mh_eff - mh_fee) > (req.amount_src * eff_d - fee_d):
                best_eff, best_sp, best_slip, best_fee, best_route, best_path = (
                    mh_eff,
                    mh_sp,
                    mh_slip,
                    mh_fee,
                    RouteQuality.MULTIHOP,
                    mh_path,
                )

        # Guard with client constraint
        limit = (
            req.max_spread_bps
            if req.max_spread_bps is not None
            else self.max_spread_bps_default
        )
        if best_sp > limit:
            # degrade to direct if spread is smaller and within limit
            if sp_d <= limit:
                best_eff, best_sp, best_slip, best_fee, best_route, best_path = (
                    eff_d,
                    sp_d,
                    slip_d,
                    fee_d,
                    RouteQuality.DIRECT,
                    [req.src, req.dst],
                )

        q = FXQuote(
            request_id=req.req_id,
            base=req.src,
            quote=req.dst,
            amount_base=req.amount_src,
            rate=round(best_eff, 8),
            spread_bps=round(best_sp, 2),
            est_slippage_bps=round(best_slip, 2),
            fees_quote=round(best_fee, 8),
            route=best_route,
            route_path=best_path,
            symbolic_coherence=round(coh, 4),
        )
        return q

    def best_route(
        self, src: FX, dst: FX, amount_src: float, urgency: float = 0.5
    ) -> Tuple[RouteQuality, List[FX]]:
        """
        Returns preferred route (direct | multihop) and path for informational UI.
        """
        eff_d, sp_d, slip_d, fee_d = self.rate_provider.direct_quote(
            src, dst, amount_src, urgency
        )
        mh_eff, mh_sp, mh_slip, mh_fee, mh_path = self.rate_provider.multihop_quote(
            src, dst, amount_src, urgency
        )
        if (amount_src * mh_eff - mh_fee) > (amount_src * eff_d - fee_d):
            return RouteQuality.MULTIHOP, mh_path
        return RouteQuality.DIRECT, [src, dst]

    def convert(self, req: ConversionRequest) -> ConversionResult:
        """
        Execute a conversion with ethos gating and record an audit footprint.
        """
        # 1) quote
        q = self.quote(req)

        # 2) ethos-gate if large or sensitive
        decision, reason = "allow", "small_transfer"
        if req.amount_src >= self.large_transfer_threshold or "sensitive" in req.tags:
            tx = {
                "id": f"fx_{req.req_id}",
                "purpose": req.purpose,
                "amount": float(req.amount_src),
                "currency": str(req.src),
                "tags": list(req.tags),
            }
            decision, reason = ethos_decision(tx)

        # 3) compute exec & amounts
        dst_amount = max(0.0, q.amount_quote - q.fees_quote)
        conv = ConversionResult(
            conversion_id=f"conv_{int(time.time())}_{uuid.uuid4().hex[:6]}",
            request_id=req.req_id,
            src=req.src,
            dst=req.dst,
            amount_src=req.amount_src,
            amount_dst=round(dst_amount, 8),
            exec_rate=q.rate,
            route=q.route,
            route_path=q.route_path,
            fees_dst=q.fees_quote,
            symbolic_coherence=q.symbolic_coherence,
            ethos_decision=decision,
            ethos_reason=reason,
        )

        # 4) if ethos denies, zero out effect (simulate controlled reject)
        if decision != "allow":
            conv.amount_dst = 0.0
            conv.exec_rate = 0.0

        # Optionally persist journal line
        self._append_journal(conv)
        return conv

    # ----------------- Risk / Policy helpers -----------------

    def policy_preview(self, req: ConversionRequest) -> Dict[str, Any]:
        """
        Fast check of what the policy engine would likely do.
        """
        decision, reason = "allow", "small_transfer"
        if req.amount_src >= self.large_transfer_threshold or "sensitive" in req.tags:
            decision, reason = ethos_decision(
                {
                    "id": f"fx_{req.req_id}",
                    "purpose": req.purpose,
                    "amount": float(req.amount_src),
                    "currency": str(req.src),
                    "tags": list(req.tags),
                }
            )
        return {"decision": decision, "reason": reason}

    # ----------------- Private helpers -----------------

    def _signals(self) -> Dict[str, Any]:
        """
        Prefer shared helper; otherwise a single local evaluation fallback.
        """
        sig = se41_signals()
        if sig:
            return sig
        try:
            s = self._se41.evaluate(assemble_se41_context())
            return getattr(s, "__dict__", {}) if hasattr(s, "__dict__") else {}
        except Exception:
            return {
                "coherence": 0.65,
                "mirror_consistency": 0.6,
                "risk": 0.2,
                "uncertainty": 0.2,
                "ethos": {
                    "authenticity": 0.9,
                    "integrity": 0.9,
                    "responsibility": 0.9,
                    "enrichment": 0.9,
                },
            }

    def _append_journal(self, conv: ConversionResult) -> None:
        """
        Append an audit JSONL line; keep the write soft-failing.
        """
        try:
            path = self.data_dir / "fx_journal.jsonl"
            rec = {
                "ts": conv.ts.isoformat(),
                "id": conv.conversion_id,
                "req": conv.request_id,
                "src": conv.src,
                "dst": conv.dst,
                "amount_src": conv.amount_src,
                "amount_dst": conv.amount_dst,
                "rate": conv.exec_rate,
                "route": conv.route.value,
                "path": conv.route_path,
                "fees_dst": conv.fees_dst,
                "coherence": conv.symbolic_coherence,
                "ethos_decision": conv.ethos_decision,
                "ethos_reason": conv.ethos_reason,
            }
            with path.open("a", encoding="utf-8") as f:
                import json

                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception as e:
            self.logger.warning("FX journal append failed: %s", e)


# ----------------------------- Factory & CLI -----------------------------


def create_currency_conversion_ai(**kwargs) -> CurrencyConversionAI:
    return CurrencyConversionAI(**kwargs)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    print("=" * 70)
    print("EidollonaONE Currency Conversion AI v4.1+")
    print("Framework: Symbolic Equation v4.1+ with Ethos-Gated FX")
    print("Purpose: Ethical, coherent, and auditable currency conversion")
    print("=" * 70)

    try:
        fxai = create_currency_conversion_ai()
        req = ConversionRequest(
            req_id=f"fx_{uuid.uuid4().hex[:8]}",
            src="USD",
            dst="EUR",
            amount_src=25_000.0,
            purpose="treasury_funding",
            tags=["fx", "treasury"],
        )
        q = fxai.quote(req)
        print(
            f"Quote: {q.amount_base} {q.base} → {q.amount_quote} {q.quote} "
            f"at {q.rate} (spread {q.spread_bps}bps, slip {q.est_slippage_bps}bps, fees {q.fees_quote}) "
            f"[{q.route.value} {q.route_path}] coherence={q.symbolic_coherence}"
        )
        res = fxai.convert(req)
        print(
            f"Convert: decision={res.ethos_decision} reason={res.ethos_reason} "
            f"received={res.amount_dst} {res.dst} @ {res.exec_rate}"
        )

    except Exception as e:
        print(f"❌ Initialization or run failed: {e}")
