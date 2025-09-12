# trading_engine/financial_overview.py
# ===================================================================
# EidollonaONE Financial Overview — SE41 v4.1+ aligned
#
# What this module does
# - Pulls SE41Signals (coherence, risk, uncertainty, ethos, embody).
# - Computes a bounded market coherence & regime map safely.
# - Generates quantum-enhanced insights, ethos-gating “high-impact”
#   recommendations before they are surfaced.
# - Exposes compact getters for dashboard / risk / performance / insights.
# - Journals market-analysis snapshots for audit.
#
# Dependencies (first-party):
#   trading.helpers.se41_trading_gate: se41_signals, ethos_decision, se41_numeric
#   symbolic_core.symbolic_equation41 & se41_context (fallback only)
# ===================================================================

from __future__ import annotations

import logging
import statistics
import random
import time
import json
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict, List, Optional

from symbolic_core.symbolic_equation41 import SymbolicEquation41
from trading.helpers.se41_trading_gate import se41_signals, ethos_decision, se41_numeric


# --------------------------- enums & dataclasses ---------------------------


class MarketTrend(Enum):
    STRONG_BULLISH = "strong_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONG_BEARISH = "strong_bearish"
    VOLATILE = "volatile"
    CONSOLIDATING = "consolidating"


class MarketRegime(Enum):
    TRENDING = "trending"
    RANGING = "ranging"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    CRISIS = "crisis"


class AssetClass(Enum):
    STOCKS = "stocks"
    FOREX = "forex"
    CRYPTO = "crypto"
    COMMODITIES = "commodities"
    BONDS = "bonds"
    INDICES = "indices"
    OPTIONS = "options"
    FUTURES = "futures"


@dataclass
class MarketData:
    symbol: str
    price: float
    timestamp: datetime
    volume: float = 0.0
    open_price: float = 0.0
    high_price: float = 0.0
    low_price: float = 0.0
    change: float = 0.0
    change_percent: float = 0.0
    market_cap: Optional[float] = None
    volatility: float = 0.0


@dataclass
class PortfolioSummary:
    total_value: float = 0.0
    total_pnl: float = 0.0
    total_pnl_percent: float = 0.0
    day_pnl: float = 0.0
    week_pnl: float = 0.0
    month_pnl: float = 0.0

    total_positions: int = 0
    long_positions: int = 0
    short_positions: int = 0
    winning_positions: int = 0
    losing_positions: int = 0

    portfolio_beta: float = 1.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    var_95: float = 0.0

    cash_allocation: float = 0.0
    equity_allocation: float = 0.0
    bond_allocation: float = 0.0
    alternative_allocation: float = 0.0

    symbolic_coherence: float = 0.0
    quantum_stability: float = 0.0


@dataclass
class MarketInsight:
    insight_id: str
    title: str
    description: str
    category: str
    confidence: float = 0.0
    impact: str = "medium"  # low | medium | high
    timeframe: str = "short"  # short | medium | long
    symbols: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    symbolic_strength: float = 0.0
    quantum_probability: float = 0.0
    ethos_gate: str = "unknown"  # allow|hold|deny (from ethos_decision)


@dataclass
class RiskMetrics:
    portfolio_risk: float = 0.0
    concentration_risk: float = 0.0
    correlation_risk: float = 0.0
    volatility_risk: float = 0.0
    liquidity_risk: float = 0.0
    market_risk: float = 0.0

    intraday_risk: float = 0.0
    overnight_risk: float = 0.0
    weekend_risk: float = 0.0

    conditional_var: float = 0.0
    expected_shortfall: float = 0.0
    stress_test_result: float = 0.0

    symbolic_risk_coherence: float = 0.0
    quantum_risk_stability: float = 0.0


@dataclass
class PerformanceMetrics:
    total_return: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0

    win_rate: float = 0.0
    profit_factor: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0

    total_trades: int = 0
    profitable_trades: int = 0
    unprofitable_trades: int = 0
    average_trade_duration: timedelta = field(
        default_factory=lambda: timedelta(hours=1)
    )

    benchmark_correlation: float = 0.0
    alpha: float = 0.0
    beta: float = 1.0
    information_ratio: float = 0.0


# --------------------------- v4.1 helpers ---------------------------


def _min_ethos(sig: Dict[str, Any]) -> float:
    e = sig.get("ethos", {}) if isinstance(sig, dict) else {}
    if not e:
        return 0.0
    return min(
        float(e.get("authenticity", 0.0)),
        float(e.get("integrity", 0.0)),
        float(e.get("responsibility", 0.0)),
        float(e.get("enrichment", 0.0)),
    )


def _bounded_market_coherence(
    sig: Dict[str, Any], volatility: float, breadth: float, momentum: float
) -> float:
    """
    Conservative, bounded market coherence scalar [0..1].
    Dampened by risk/uncertainty and realized market turbulence.
    """
    if not sig:
        # minimal proxy without signals
        base = max(
            0.0,
            min(
                1.0,
                0.55 + 0.15 * momentum + 0.15 * (breadth - 0.5) * 2 - 0.2 * volatility,
            ),
        )
        return base

    coh = float(sig.get("coherence", 0.0))
    mc = float(sig.get("mirror_consistency", 0.0))
    me = _min_ethos(sig)
    risk = float(sig.get("risk", 0.25))
    unc = float(sig.get("uncertainty", 0.25))

    raw = 0.45 * coh + 0.25 * mc + 0.20 * me + 0.10 * max(-1.0, min(1.0, momentum))
    damp = max(0.35, 1.0 - 0.35 * (risk + unc) - 0.20 * volatility)
    return max(0.0, min(1.0, raw * damp))


# --------------------------- Symbolic market analyzer ---------------------------


class SymbolicMarketAnalyzer:
    """Symbolic equation-based market analysis (SE41)."""

    def __init__(self, journal_dir: Optional[Path] = None) -> None:
        self.logger = logging.getLogger(f"{__name__}.SymbolicMarketAnalyzer")
        self._se41 = SymbolicEquation41()  # only for guarded numeric fallback
        self._journal_dir = Path(journal_dir or "financial_overview_data")
        self._journal_dir.mkdir(exist_ok=True)
        self._snap_path = self._journal_dir / "market_snapshots.jsonl"

    def analyze(
        self, market_data: List[MarketData], portfolio_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute a bounded coherence, infer trend/regime, and return a compact payload.
        Falls back to guarded numeric if se41_signals() returns empty.
        """
        try:
            if not market_data:
                return self._emit(
                    {
                        "coherence": 0.5,
                        "trend": MarketTrend.NEUTRAL.value,
                        "regime": MarketRegime.RANGING.value,
                        "confidence": 0.5,
                    }
                )

            # Aggregates
            avg_volatility = statistics.mean(
                [max(0.0, min(1.0, d.volatility)) for d in market_data]
            )
            price_changes = [d.change_percent for d in market_data]
            momentum_raw = statistics.mean(price_changes) if price_changes else 0.0
            momentum = max(-1.0, min(1.0, momentum_raw / 5.0))
            pos_changes = sum(1 for c in price_changes if c > 0)
            breadth = (pos_changes / len(price_changes)) if price_changes else 0.5

            sig = se41_signals()
            if not sig:
                # guarded numeric synthesis
                try:
                    _ = se41_numeric(
                        M_t=breadth,
                        DNA_states=[1.0, 1.0, avg_volatility, momentum, breadth, 1.1],
                        harmonic_patterns=[
                            1.0,
                            1.1,
                            avg_volatility,
                            momentum,
                            breadth,
                            1.2,
                        ],
                    )
                except Exception:
                    pass  # purely for side effects; coherence computed below

            coherence = _bounded_market_coherence(
                sig or {}, avg_volatility, breadth, momentum
            )

            # Trend & regime
            trend = self._trend(momentum, avg_volatility, breadth, coherence).value
            regime = self._regime(avg_volatility, momentum, breadth, coherence).value
            conf = self._confidence(coherence, avg_volatility, breadth)

            payload = {
                "coherence": coherence,
                "trend": trend,
                "regime": regime,
                "confidence": conf,
                "momentum": momentum,
                "volatility": avg_volatility,
                "breadth": breadth,
                "signals": sig or {},
                "ts": datetime.now().isoformat(),
            }
            return self._emit(payload)
        except Exception as e:
            self.logger.error("Market analysis failed: %s", e)
            return self._emit(
                {
                    "coherence": 0.5,
                    "trend": MarketTrend.NEUTRAL.value,
                    "regime": MarketRegime.RANGING.value,
                    "confidence": 0.5,
                    "error": str(e),
                }
            )

    def _trend(
        self, momentum: float, vol: float, breadth: float, coh: float
    ) -> MarketTrend:
        try:
            if coh > 0.8 and abs(momentum) > 0.6:
                return (
                    MarketTrend.STRONG_BULLISH
                    if momentum > 0
                    else MarketTrend.STRONG_BEARISH
                )
            if coh > 0.6 and abs(momentum) > 0.3:
                return MarketTrend.BULLISH if momentum > 0 else MarketTrend.BEARISH
            if vol > 0.6:
                return MarketTrend.VOLATILE
            if abs(momentum) < 0.2 and vol < 0.3:
                return MarketTrend.CONSOLIDATING
            return MarketTrend.NEUTRAL
        except Exception:
            return MarketTrend.NEUTRAL

    def _regime(
        self, vol: float, momentum: float, breadth: float, coh: float
    ) -> MarketRegime:
        try:
            if vol > 0.7:
                return (
                    MarketRegime.CRISIS if coh < 0.4 else MarketRegime.HIGH_VOLATILITY
                )
            if vol < 0.2:
                return MarketRegime.LOW_VOLATILITY
            if abs(momentum) > 0.5 and coh > 0.6:
                return MarketRegime.TRENDING
            if vol > 0.4 and abs(momentum) > 0.4:
                return MarketRegime.BREAKOUT
            if breadth > 0.7 or breadth < 0.3:
                return MarketRegime.REVERSAL
            return MarketRegime.RANGING
        except Exception:
            return MarketRegime.RANGING

    def _confidence(self, coh: float, vol: float, breadth: float) -> float:
        try:
            return max(
                0.0,
                min(
                    1.0,
                    0.5 * coh
                    + 0.3 * (1.0 - min(vol, 1.0))
                    + 0.2 * abs(breadth - 0.5) * 2,
                ),
            )
        except Exception:
            return 0.5

    def _emit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Append snapshot to journal (best-effort) and return payload."""
        try:
            with self._snap_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            pass
        return payload


# --------------------------- quantum financial intelligence ---------------------------


class QuantumFinancialIntelligence:
    """Quantum-enhanced insights with ethos gating."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.QuantumFinancialIntelligence")

    def insights(
        self,
        market: Dict[str, Any],
        portfolio: Dict[str, Any],
        historical: Dict[str, Any],
        max_items: int = 10,
    ) -> List[MarketInsight]:
        """
        Generate insights, enhance with a quantum adjustment, and ethos-gate any
        high-impact recommendations (“impact” == high or confidence >= 0.8).
        """
        out: List[MarketInsight] = []
        try:
            out.extend(self._trend_insights(market))
            out.extend(self._risk_insights(market, portfolio))
            out.extend(self._opportunity_insights(market, portfolio, historical))
            out.extend(self._performance_insights(portfolio))

            for ins in out:
                self._enhance_insight_quantum(ins, market)
                # Ethos-gate only high-impact suggestions
                if ins.impact == "high" or ins.confidence >= 0.8:
                    allow, reason = ethos_decision(
                        {
                            "id": ins.insight_id,
                            "purpose": f"insight:{ins.category}",
                            "amount": float(portfolio.get("total_value", 1e5))
                            * 0.05,  # 5% notional proxy
                            "currency": "NOM",
                            "tags": ["insight", ins.category],
                        }
                    )
                    ins.ethos_gate = f"{allow}:{reason}" if reason else allow

            out.sort(key=lambda i: i.confidence * i.quantum_probability, reverse=True)
            return out[:max_items]
        except Exception as e:
            self.logger.error("Insight generation failed: %s", e)
            return []

    # ---- atomic generators ----

    def _trend_insights(self, market: Dict[str, Any]) -> List[MarketInsight]:
        r: List[MarketInsight] = []
        try:
            trend = MarketTrend(market.get("trend", MarketTrend.NEUTRAL))
        except Exception:
            trend = MarketTrend.NEUTRAL
        coh = float(market.get("coherence", 0.5))
        conf = float(market.get("confidence", 0.5))

        now = int(time.time())
        if trend == MarketTrend.STRONG_BULLISH and coh > 0.8:
            r.append(
                MarketInsight(
                    insight_id=f"bullish_{now}",
                    title="Strong Bullish Trend Confirmed",
                    description="High coherence + strong momentum — consider adding quality longs.",
                    category="trend",
                    confidence=conf,
                    impact="high",
                    timeframe="medium",
                )
            )
        elif trend == MarketTrend.STRONG_BEARISH and coh > 0.8:
            r.append(
                MarketInsight(
                    insight_id=f"bearish_{now}",
                    title="Strong Bearish Trend Warning",
                    description="High coherence to downside — consider defensive hedges or shorts.",
                    category="trend",
                    confidence=conf,
                    impact="high",
                    timeframe="medium",
                )
            )
        elif trend == MarketTrend.VOLATILE and coh < 0.55:
            r.append(
                MarketInsight(
                    insight_id=f"volatile_{now}",
                    title="High Volatility Caution",
                    description="Volatility elevated with modest coherence — reduce gross and tighten stops.",
                    category="risk",
                    confidence=conf,
                    impact="medium",
                    timeframe="short",
                )
            )
        return r

    def _risk_insights(
        self, market: Dict[str, Any], portfolio: Dict[str, Any]
    ) -> List[MarketInsight]:
        r: List[MarketInsight] = []
        vol = float(market.get("volatility", 0.3))
        prsk = float(portfolio.get("risk_level", 0.3))
        now = int(time.time())
        if vol > 0.7 and prsk > 0.6:
            r.append(
                MarketInsight(
                    insight_id=f"risk_hi_{now}",
                    title="Elevated Market & Portfolio Risk",
                    description="Both market volatility and portfolio risk are elevated.",
                    category="risk",
                    confidence=0.8,
                    impact="high",
                    timeframe="short",
                )
            )
        elif vol < 0.2 and prsk < 0.3:
            r.append(
                MarketInsight(
                    insight_id=f"risk_lo_{now}",
                    title="Low Risk Window",
                    description="Quiet regime; consider measured deployment into high-quality ideas.",
                    category="opportunity",
                    confidence=0.7,
                    impact="medium",
                    timeframe="medium",
                )
            )
        return r

    def _opportunity_insights(
        self,
        market: Dict[str, Any],
        portfolio: Dict[str, Any],
        historical: Dict[str, Any],
    ) -> List[MarketInsight]:
        r: List[MarketInsight] = []
        breadth = float(market.get("breadth", 0.5))
        regime = (
            MarketRegime(market.get("regime", MarketRegime.RANGING))
            if isinstance(market.get("regime"), str) is False
            else MarketRegime(market.get("regime", MarketRegime.RANGING))
        )
        now = int(time.time())
        if regime == MarketRegime.BREAKOUT and breadth > 0.6:
            r.append(
                MarketInsight(
                    insight_id=f"breakout_{now}",
                    title="Breakout Dynamics",
                    description="Breadth-supported breakout — momentum carries positive expectancy.",
                    category="opportunity",
                    confidence=0.7,
                    impact="medium",
                    timeframe="short",
                )
            )
        elif regime == MarketRegime.REVERSAL:
            r.append(
                MarketInsight(
                    insight_id=f"reversal_{now}",
                    title="Potential Reversal",
                    description="Reversal conditions — monitor confirmation; mean-reversion setups likely.",
                    category="opportunity",
                    confidence=0.6,
                    impact="medium",
                    timeframe="medium",
                )
            )
        return r

    def _performance_insights(self, portfolio: Dict[str, Any]) -> List[MarketInsight]:
        r: List[MarketInsight] = []
        win = float(portfolio.get("win_rate", 0.5))
        shp = float(portfolio.get("sharpe_ratio", 0.0))
        now = int(time.time())
        if win > 0.7 and shp > 1.0:
            r.append(
                MarketInsight(
                    insight_id=f"perf_strong_{now}",
                    title="Strong Performance",
                    description="High win-rate and Sharpe; reinforce working playbooks; avoid drift.",
                    category="performance",
                    confidence=0.8,
                    impact="low",
                    timeframe="long",
                )
            )
        elif win < 0.4 or shp < 0.5:
            r.append(
                MarketInsight(
                    insight_id=f"perf_review_{now}",
                    title="Performance Review",
                    description="Sub-target performance; tighten risk, review stop policy, refit signals.",
                    category="performance",
                    confidence=0.7,
                    impact="medium",
                    timeframe="medium",
                )
            )
        return r

    def _enhance_insight_quantum(
        self, ins: MarketInsight, market: Dict[str, Any]
    ) -> None:
        try:
            q = random.uniform(0.9, 1.1)
            coh = float(market.get("coherence", 0.5))
            base = (coh + ins.confidence) / 2.0
            ins.quantum_probability = max(0.0, min(1.0, base * q))
            ins.symbolic_strength = max(0.0, min(1.0, ins.confidence * coh * q))
        except Exception:
            ins.quantum_probability = ins.confidence
            ins.symbolic_strength = ins.confidence


# --------------------------- Financial Overview (facade) ---------------------------


class FinancialOverview:
    """
    Comprehensive market/portfolio overview with SE41 signals, bounded coherence,
    quantum-enhanced insights, and ethos-gated high-impact suggestions.
    """

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self.logger = logging.getLogger(f"{__name__}.FinancialOverview")
        self._dir = Path(data_dir or "financial_overview_data")
        self._dir.mkdir(exist_ok=True)
        self._insights_path = self._dir / "insights.jsonl"

        # Subsystems
        self.market_analyzer = SymbolicMarketAnalyzer(journal_dir=self._dir)
        self.quantum_intel = QuantumFinancialIntelligence()

        # State
        self.market_data: Dict[str, MarketData] = {}
        self.portfolio_summary = PortfolioSummary()
        self.risk_metrics = RiskMetrics()
        self.performance = PerformanceMetrics()

        # History (light)
        self.price_history = defaultdict(lambda: deque(maxlen=1000))
        self.volume_history = defaultdict(lambda: deque(maxlen=1000))
        self.pnl_history = deque(maxlen=1000)

        # Config
        self.analysis_interval = 30  # seconds
        self.max_insights = 15
        self.risk_threshold = 0.7
        self.last_analysis = datetime.min

        self.logger.info("Financial Overview v4.1+ initialized (SE41 ready).")

    # ---- public API ----

    def analyze_and_insights(
        self, portfolio_ctx: Dict[str, Any], historical_ctx: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run a single analysis pass and return:
        - market (coherence/trend/regime/confidence/vol/breadth)
        - risk (lightweight)
        - performance (pass-through)
        - insights (ethos-gated & quantum-enhanced, top N)
        """
        # Build list from current market_data dictionary
        md_list = list(self.market_data.values())
        market = self.market_analyzer.analyze(md_list, portfolio_ctx)
        risk = self._estimate_risk(market, portfolio_ctx)
        perf = self._current_performance_dict()

        insights = self.quantum_intel.insights(
            market=market,
            portfolio=portfolio_ctx,
            historical=historical_ctx,
            max_items=self.max_insights,
        )
        self._append_insights(insights)

        return {
            "market": market,
            "risk": risk,
            "performance": perf,
            "insights": [self._insight_to_dict(i) for i in insights],
            "ts": datetime.now().isoformat(),
        }

    def update_market_point(self, d: MarketData) -> None:
        self.market_data[d.symbol] = d
        self.price_history[d.symbol].append((d.timestamp.isoformat(), d.price))
        self.volume_history[d.symbol].append((d.timestamp.isoformat(), d.volume))

    def set_portfolio_snapshot(
        self,
        summary: PortfolioSummary,
        risk: Optional[RiskMetrics] = None,
        performance: Optional[PerformanceMetrics] = None,
    ) -> None:
        self.portfolio_summary = summary
        if risk:
            self.risk_metrics = risk
        if performance:
            self.performance = performance

    # ---- internal helpers ----

    def _estimate_risk(
        self, market: Dict[str, Any], portfolio: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            vol = float(market.get("volatility", 0.3))
            coh = float(market.get("coherence", 0.5))
            size = float(portfolio.get("total_value", 1e5))
            # Simple blended risk index (0..1)
            idx = max(0.0, min(1.0, 0.6 * vol + 0.4 * (1.0 - coh)))
            var95 = size * (0.015 + 0.10 * vol)  # toy proxy
            return {"risk_index": idx, "var_95": var95}
        except Exception:
            return {
                "risk_index": 0.5,
                "var_95": float(portfolio.get("total_value", 1e5)) * 0.02,
            }

    def _current_performance_dict(self) -> Dict[str, Any]:
        p = self.performance
        return {
            "total_return": p.total_return,
            "annualized_return": p.annualized_return,
            "volatility": p.volatility,
            "sharpe_ratio": p.sharpe_ratio,
            "win_rate": p.win_rate,
            "profit_factor": p.profit_factor,
            "trades": p.total_trades,
        }

    def _append_insights(self, items: List[MarketInsight]) -> None:
        try:
            if not items:
                return
            with self._insights_path.open("a", encoding="utf-8") as f:
                for i in items:
                    f.write(
                        json.dumps(self._insight_to_dict(i), ensure_ascii=False) + "\n"
                    )
        except Exception:
            pass

    def _insight_to_dict(self, i: MarketInsight) -> Dict[str, Any]:
        return {
            "id": i.insight_id,
            "title": i.title,
            "desc": i.description,
            "category": i.category,
            "confidence": i.confidence,
            "impact": i.impact,
            "timeframe": i.timeframe,
            "symbols": i.symbols,
            "ts": i.timestamp.isoformat(),
            "symbolic_strength": i.symbolic_strength,
            "quantum_probability": i.quantum_probability,
            "ethos_gate": i.ethos_gate,
        }


# --------------------------- factory & demo ---------------------------


def create_financial_overview(**kwargs) -> FinancialOverview:
    return FinancialOverview(**kwargs)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    print("=" * 72)
    print("EidollonaONE Financial Overview v4.1+  —  coherent • ethical • auditable")
    print("=" * 72)
    try:
        ov = create_financial_overview()
        # minimal demo feed (static point)
        now = datetime.now()
        ov.update_market_point(
            MarketData(
                symbol="DEMO",
                price=100.0,
                timestamp=now,
                volume=1e6,
                open_price=98.0,
                high_price=102.0,
                low_price=97.5,
                change=2.0,
                change_percent=2.0,
                volatility=0.28,
            )
        )
        dashboard = ov.analyze_and_insights(
            portfolio_ctx={"total_value": 150_000.0, "risk_level": 0.35},
            historical_ctx={},
        )
        print(json.dumps(dashboard, indent=2))
    except Exception as e:
        print("❌ Initialization failed:", e)
