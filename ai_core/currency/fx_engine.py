"""Advanced FX currency engine (SE41‑aligned v4.1 style).

Features
--------
* Backward compatible :class:`FXRateEngine.evaluate_pair` (simple single pair evaluation).
* New rolling multi‑pair analytics via :class:`AdvancedFXEngine`.
* Rolling window spread statistics & z‑scores.
* Volatility (realized) on mid price, correlation matrix (lightweight, pairwise).
* Triangular arbitrage deviation detection (A/B * B/C vs A/C) with tolerance.
* Composite symbolic health scoring using SE41 (with safe fallbacks if unavailable).
* Deterministic stability score and explanation string for logging / monitoring.

Safe Fallbacks
--------------
If symbolic_core modules are missing a stub context & signal struct is used so the
engine still functions for tests / dry runs.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List, Deque, Tuple
from collections import deque
import math
import statistics
import time

try:  # pragma: no cover - runtime optional dependency
    from symbolic_core.symbolic_equation import SymbolicEquation41, SE41Signals  # type: ignore
    from symbolic_core.context_builder import assemble_se41_context  # type: ignore
except Exception:  # pragma: no cover

    class SE41Signals:  # minimal stub
        def __init__(
            self, risk: float = 0.4, uncertainty: float = 0.4, coherence: float = 0.6
        ):
            self.risk = risk
            self.uncertainty = uncertainty
            self.coherence = coherence

    class SymbolicEquation41:  # type: ignore
        def evaluate(self, ctx: Dict[str, Any]) -> SE41Signals:  # noqa: D401
            # naive scoring from hints
            r = float(ctx.get("risk_hint", 0.4))
            u = float(ctx.get("uncertainty_hint", 0.4))
            c = float(ctx.get("coherence_hint", 0.6))
            return SE41Signals(risk=r, uncertainty=u, coherence=c)

    def assemble_se41_context(**kwargs):  # type: ignore
        return kwargs


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class FXSignal:
    pair: str
    mid: float
    spread_pips: float
    se41: SE41Signals
    stability: float  # derived 1 - (risk + uncertainty)/2
    explain: str
    # Extended fields (safe default when produced by AdvancedFXEngine)
    spread_z: Optional[float] = None
    realized_vol: Optional[float] = None
    window: int = 1


@dataclass
class FXPairWindow:
    spreads: Deque[float] = field(default_factory=deque)
    mids: Deque[float] = field(default_factory=deque)

    def push(self, spread_pips: float, mid: float, maxlen: int) -> None:
        self.spreads.append(spread_pips)
        self.mids.append(mid)
        if len(self.spreads) > maxlen:
            self.spreads.popleft()
        if len(self.mids) > maxlen:
            self.mids.popleft()

    def spread_stats(self) -> Tuple[float, float]:
        if len(self.spreads) < 2:
            return float(self.spreads[-1]) if self.spreads else 0.0, 0.0
        return statistics.mean(self.spreads), statistics.pstdev(self.spreads)

    def realized_vol(self) -> float:
        if len(self.mids) < 2:
            return 0.0
        rets: List[float] = []
        prev = self.mids[0]
        for m in list(self.mids)[1:]:
            if prev:
                rets.append(math.log(m / prev))
            prev = m
        if not rets:
            return 0.0
        return statistics.pstdev(rets) * math.sqrt(
            252 * 24 * 60
        )  # annualized (assuming minute bars)


@dataclass
class TriangularDeviation:
    path: Tuple[str, str, str]
    implied: float
    direct: float
    deviation_pct: float
    explain: str


@dataclass
class CompositeFXSnapshot:
    ts: float
    signals: Dict[str, FXSignal]
    triangular: List[TriangularDeviation]
    correlation: Dict[Tuple[str, str], float]


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
def _safe_div(n: float, d: float, default: float = 0.0) -> float:
    return (
        n / d
        if (d not in (0, 0.0) and math.isfinite(n) and math.isfinite(d))
        else default
    )


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


# ---------------------------------------------------------------------------
# Backward compatible simple engine
# ---------------------------------------------------------------------------
class FXRateEngine:
    """Single pair evaluation (legacy API retained)."""

    def __init__(self, symbolic: Optional[SymbolicEquation41] = None) -> None:
        self.symbolic = symbolic or SymbolicEquation41()

    def evaluate_pair(
        self, pair: str, bids: List[float], asks: List[float]
    ) -> FXSignal:
        if not bids or not asks:
            bids = bids or [1.0]
            asks = asks or [1.0]
        bid = float(bids[-1])
        ask = float(asks[-1])
        mid = (bid + ask) / 2.0 if (bid and ask) else 1.0
        spread = max(0.0, ask - bid)
        spread_pips = spread * 10_000.0 / mid if mid else 0.0
        risk_hint = min(0.9, 0.10 + spread_pips / 1000.0)
        uncertainty_hint = min(0.95, 0.25 + spread_pips / 800.0)
        coherence_hint = max(0.40, 0.85 - spread_pips / 500.0)
        ctx = assemble_se41_context(
            coherence_hint=coherence_hint,
            risk_hint=risk_hint,
            uncertainty_hint=uncertainty_hint,
            extras={"fx": {"pair": pair, "spread_pips": spread_pips}},
        )
        se = self.symbolic.evaluate(ctx)
        stability = _clamp01(1.0 - (se.risk + se.uncertainty) / 2.0)
        return FXSignal(
            pair=pair,
            mid=mid,
            spread_pips=spread_pips,
            se41=se,
            stability=stability,
            explain=f"spread={spread_pips:.2f}p risk={se.risk:.2f} unc={se.uncertainty:.2f}",
            spread_z=None,
            realized_vol=None,
            window=1,
        )


# ---------------------------------------------------------------------------
# Advanced multi-pair engine
# ---------------------------------------------------------------------------
class AdvancedFXEngine:
    """Multi‑pair rolling analytics & symbolic composite evaluation.

    Usage::
        engine = AdvancedFXEngine(window=50)
        engine.update("EURUSD", bid, ask)
        snap = engine.snapshot()
    """

    def __init__(
        self,
        window: int = 60,
        triangular_sets: Optional[List[Tuple[str, str, str]]] = None,
        symbolic: Optional[SymbolicEquation41] = None,
    ) -> None:
        self.window = max(5, window)
        self.symbolic = symbolic or SymbolicEquation41()
        self._pairs: Dict[str, FXPairWindow] = {}
        # Triangular sets: e.g. [("EURUSD","USDJPY","EURJPY")] order matters: A/B, B/C, A/C
        self.triangular_sets = triangular_sets or []

    # --- Data ingestion --------------------------------------------------
    def update(self, pair: str, bid: float, ask: float) -> FXSignal:
        bid = float(bid)
        ask = float(ask)
        mid = (bid + ask) / 2.0 if (bid and ask) else 1.0
        spread_pips = (max(0.0, ask - bid) * 10_000.0 / mid) if mid else 0.0
        window = self._pairs.setdefault(pair, FXPairWindow())
        window.push(spread_pips, mid, self.window)
        mean_spread, std_spread = window.spread_stats()
        spread_z = (
            (spread_pips - mean_spread) / std_spread if std_spread > 1e-12 else 0.0
        )
        realized_vol = window.realized_vol()
        # Hints: larger spread_z => higher risk & uncertainty; higher vol => more uncertainty
        risk_hint = _clamp01(0.08 + abs(spread_z) * 0.15 + spread_pips / 8000.0)
        uncertainty_hint = _clamp01(0.20 + realized_vol * 0.05 + abs(spread_z) * 0.1)
        coherence_hint = _clamp01(0.9 - abs(spread_z) * 0.1 - realized_vol * 0.05)
        ctx = assemble_se41_context(
            risk_hint=risk_hint,
            uncertainty_hint=uncertainty_hint,
            coherence_hint=coherence_hint,
            extras={
                "fx": {
                    "pair": pair,
                    "spread_pips": spread_pips,
                    "spread_z": spread_z,
                    "realized_vol": realized_vol,
                }
            },
        )
        se = self.symbolic.evaluate(ctx)
        stability = _clamp01(1.0 - (se.risk + se.uncertainty) / 2.0)
        return FXSignal(
            pair=pair,
            mid=mid,
            spread_pips=spread_pips,
            se41=se,
            stability=stability,
            explain=f"z={spread_z:+.2f} spread={spread_pips:.2f} vol={realized_vol:.4f}",
            spread_z=spread_z,
            realized_vol=realized_vol,
            window=len(window.spreads),
        )

    # --- Analytics -------------------------------------------------------
    def _triangular_checks(self, mids: Dict[str, float]) -> List[TriangularDeviation]:
        out: List[TriangularDeviation] = []
        for a_b, b_c, a_c in self.triangular_sets:
            if a_b in mids and b_c in mids and a_c in mids:
                implied = mids[a_b] * mids[b_c]
                direct = mids[a_c]
                if direct and implied:
                    dev = abs(implied - direct) / direct
                else:
                    dev = 0.0
                out.append(
                    TriangularDeviation(
                        path=(a_b, b_c, a_c),
                        implied=implied,
                        direct=direct,
                        deviation_pct=dev,
                        explain=f"{a_b}*{b_c}->{a_c} dev={dev*100:.3f}%",
                    )
                )
        return out

    def _pairwise_correlation(self) -> Dict[Tuple[str, str], float]:
        # Compute correlation on overlapping window lengths of log returns.
        series: Dict[str, List[float]] = {}
        for pair, window in self._pairs.items():
            mids_list = list(window.mids)
            if len(mids_list) < 3:
                continue
            rets = []
            prev = mids_list[0]
            for m in mids_list[1:]:
                if prev:
                    rets.append(math.log(m / prev))
                prev = m
            if len(rets) >= 2:
                series[pair] = rets
        keys = list(series.keys())
        corr: Dict[Tuple[str, str], float] = {}
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                a, b = keys[i], keys[j]
                sa, sb = series[a], series[b]
                n = min(len(sa), len(sb))
                if n < 5:
                    continue
                xa = sa[-n:]
                xb = sb[-n:]
                ma = statistics.mean(xa)
                mb = statistics.mean(xb)
                num = sum((xa[k] - ma) * (xb[k] - mb) for k in range(n))
                da = math.sqrt(sum((xa[k] - ma) ** 2 for k in range(n)))
                db = math.sqrt(sum((xb[k] - mb) ** 2 for k in range(n)))
                c = num / (da * db) if da and db else 0.0
                corr[(a, b)] = max(-1.0, min(1.0, c))
        return corr

    # --- Public composite snapshot --------------------------------------
    def snapshot(self) -> CompositeFXSnapshot:
        signals: Dict[str, FXSignal] = {}
        mids: Dict[str, float] = {}
        for pair, window in self._pairs.items():
            # Use latest mid/spread to refresh signal without pushing new obs
            if not window.mids:
                continue
            mid = window.mids[-1]
            spread_pips = window.spreads[-1] if window.spreads else 0.0
            sig = self.update(
                pair,
                mid - (spread_pips / 10_000.0) * mid / 2,
                mid + (spread_pips / 10_000.0) * mid / 2,
            )  # approximate synthetic bid/ask
            signals[pair] = sig
            mids[pair] = sig.mid
        tri = self._triangular_checks(mids)
        corr = self._pairwise_correlation()
        return CompositeFXSnapshot(
            ts=time.time(), signals=signals, triangular=tri, correlation=corr
        )


# ---------------------------------------------------------------------------
# Minimal self-test utility
# ---------------------------------------------------------------------------
def _selftest() -> int:  # pragma: no cover
    eng = AdvancedFXEngine(window=20, triangular_sets=[("EURUSD", "USDJPY", "EURJPY")])
    # Simulate updates
    for _ in range(25):
        eng.update("EURUSD", 1.1000, 1.1002)
        eng.update("USDJPY", 150.00, 150.01)
        # derive synthetic EURJPY ~ EURUSD*USDJPY
        eurjpy_mid = 1.1001 * 150.005
        eng.update("EURJPY", eurjpy_mid - 0.01, eurjpy_mid + 0.01)
    snap = eng.snapshot()
    assert snap.signals, "No signals produced"
    print("Snapshot signals:", {k: v.stability for k, v in snap.signals.items()})
    if snap.triangular:
        print("Tri dev sample:", snap.triangular[0].explain)
    return 0


__all__ = [
    "FXRateEngine",
    "FXSignal",
    "AdvancedFXEngine",
    "CompositeFXSnapshot",
    "TriangularDeviation",
]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json as _json

    ap = argparse.ArgumentParser(description="Advanced FX Engine selftest / snapshot")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    eng = AdvancedFXEngine(window=15)
    for _ in range(18):
        eng.update("EURUSD", 1.10, 1.10015)
        eng.update("GBPUSD", 1.25, 1.25025)
    snap = eng.snapshot()
    print(
        _json.dumps(
            {
                "ts": snap.ts,
                "pairs": {p: asdict(sig) for p, sig in snap.signals.items()},
                "triangular": [asdict(t) for t in snap.triangular],
                "correlation_keys": [f"{a}|{b}" for (a, b) in snap.correlation.keys()],
            },
            indent=2,
        )
    )
