"""SE41 v4.1+ Market Intelligence Analyzer

Ingests ticks, news, macro snapshots → builds features (breadth, momentum,
realized vol, spreads, depth). Reads SE41Signals to classify trend & regime,
derive confidence, and emit ranked insights (trend, risk, opportunity, macro,
performance). Ethos-gates any *increase exposure* style suggestions.
Appends snapshots & insights to JSONL for full audit / replay.
"""

from __future__ import annotations

import json
import logging
import math
import random
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from symbolic_core.symbolic_equation41 import SymbolicEquation41
from trading.helpers.se41_trading_gate import se41_signals, ethos_decision, se41_numeric


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


class Sentiment(Enum):
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


@dataclass
class MarketTick:
    symbol: str
    price: float
    volume: float
    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None
    depth_bid: Optional[float] = None
    depth_ask: Optional[float] = None


@dataclass
class NewsEvent:
    title: str
    body: str
    source: str
    timestamp: datetime
    symbol_tags: List[str] = field(default_factory=list)
    sentiment: Sentiment = Sentiment.NEUTRAL
    impact: str = "medium"


@dataclass
class MacroSnapshot:
    timestamp: datetime
    vix: float = 18.0
    rates_2y: float = 0.04
    rates_10y: float = 0.045
    cpi_yoy: float = 0.03
    pmis: float = 50.0
    liquidity_proxy: float = 0.5
    growth_proxy: float = 0.5


@dataclass
class AnalysisSnapshot:
    ts: datetime
    symbols_covered: int
    avg_price: float
    total_volume: float
    realized_vol: float
    momentum: float
    breadth: float
    avg_spread_bp: float
    avg_depth_score: float
    macro_risk: float
    coherence: float
    confidence: float
    trend: MarketTrend
    regime: MarketRegime
    se41_brief: Dict[str, float]


@dataclass
class IntelligenceInsight:
    insight_id: str
    category: str
    title: str
    description: str
    symbols: List[str] = field(default_factory=list)
    confidence: float = 0.0
    impact: str = "medium"
    timeframe: str = "short"
    symbolic_strength: float = 0.0
    quantum_probability: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MarketIntelConfig:
    tick_window: int = 600
    roll_returns: int = 300
    journal_dir: str = "market_intel_data"
    max_insights: int = 12
    vol_high: float = 0.30
    vol_low: float = 0.10
    momentum_strong: float = 0.40
    breadth_extreme: float = 0.70


class MarketIntelligenceAnalyzer:
    """SE41 Market Intelligence: features → classification → insights with auditing."""

    def __init__(self, config: Optional[MarketIntelConfig] = None):
        self.cfg = config or MarketIntelConfig()
        self.logger = logging.getLogger(f"{__name__}.MarketIntelligenceAnalyzer")
        self._se41 = SymbolicEquation41()
        self._ticks: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.cfg.tick_window)
        )
        self._news: deque[NewsEvent] = deque(maxlen=2000)
        self._macro: Optional[MacroSnapshot] = None
        self._dir = Path(self.cfg.journal_dir)
        self._dir.mkdir(exist_ok=True)
        self._journal_path = self._dir / "market_intel_journal.jsonl"

    # ingestion
    def ingest_tick(self, tick: MarketTick) -> None:
        self._ticks[tick.symbol].append(tick)

    def ingest_news(self, evt: NewsEvent) -> None:
        self._news.append(evt)

    def set_macro(self, snap: MacroSnapshot) -> None:
        self._macro = snap

    # feature building
    def _features(self) -> Dict[str, Any]:
        syms = list(self._ticks.keys())
        if not syms:
            return {
                "symbols_covered": 0,
                "avg_price": 0.0,
                "total_volume": 0.0,
                "realized_vol": 0.0,
                "momentum": 0.0,
                "breadth": 0.5,
                "avg_spread_bp": 0.0,
                "avg_depth_score": 0.0,
            }
        prices = []
        vols = []
        spreads_bp = []
        depth_scores = []
        up_count = 0
        ret_series = []
        now = datetime.now()
        for s in syms:
            dq = self._ticks[s]
            if not dq:
                continue
            last = dq[-1]
            prices.append(last.price)
            vols.append(sum(t.volume for t in dq if (now - t.timestamp).seconds <= 60))
            if last.spread is not None and last.price > 0:
                spreads_bp.append(10_000.0 * (last.spread / last.price))
            else:
                if last.bid and last.ask and last.price > 0:
                    sp = max(0.0, last.ask - last.bid)
                    spreads_bp.append(10_000.0 * (sp / last.price))
            if last.depth_bid is not None and last.depth_ask is not None:
                total = (last.depth_bid + last.depth_ask) or 1.0
                depth_scores.append(
                    min(
                        max(min(last.depth_bid, last.depth_ask) / total * 2.0, 0.0), 1.0
                    )
                )
            if len(dq) >= 2:
                p0 = dq[-2].price or 1e-9
                r = math.log(max(last.price, 1e-9) / max(p0, 1e-9))
                ret_series.append(r)
                if r > 0:
                    up_count += 1
        avg_price = statistics.mean(prices) if prices else 0.0
        total_volume = sum(vols) if vols else 0.0
        avg_spread_bp = statistics.mean(spreads_bp) if spreads_bp else 0.0
        avg_depth = statistics.mean(depth_scores) if depth_scores else 0.0
        if len(ret_series) >= 5:
            var_r = statistics.pvariance(ret_series)
            realized_vol = math.sqrt(max(var_r, 0.0) * 86_400 * 365)
            momentum = statistics.mean(ret_series) * 86_400
        else:
            realized_vol = 0.0
            momentum = 0.0
        breadth = up_count / max(len(ret_series), 1)
        return {
            "symbols_covered": len(syms),
            "avg_price": avg_price,
            "total_volume": total_volume,
            "realized_vol": min(max(realized_vol, 0.0), 2.0),
            "momentum": max(min(momentum, 1.0), -1.0),
            "breadth": breadth if ret_series else 0.5,
            "avg_spread_bp": avg_spread_bp,
            "avg_depth_score": avg_depth,
        }

    # classification
    def _trend_regime(
        self, features: Dict[str, Any], se: Dict[str, Any]
    ) -> tuple[MarketTrend, MarketRegime]:
        vol = float(features["realized_vol"])
        mom = float(features["momentum"])
        brd = float(features["breadth"])
        coh = float(se.get("coherence", 0.5))
        if coh > 0.8 and abs(mom) > 0.6:
            trend = (
                MarketTrend.STRONG_BULLISH if mom > 0 else MarketTrend.STRONG_BEARISH
            )
        elif coh > 0.6 and abs(mom) > 0.3:
            trend = MarketTrend.BULLISH if mom > 0 else MarketTrend.BEARISH
        elif vol > self.cfg.vol_high:
            trend = MarketTrend.VOLATILE
        elif abs(mom) < 0.15 and vol < self.cfg.vol_low:
            trend = MarketTrend.CONSOLIDATING
        else:
            trend = MarketTrend.NEUTRAL
        if vol > self.cfg.vol_high and coh < 0.4:
            regime = MarketRegime.CRISIS
        elif vol > self.cfg.vol_high:
            regime = MarketRegime.HIGH_VOLATILITY
        elif vol < self.cfg.vol_low:
            regime = MarketRegime.LOW_VOLATILITY
        elif abs(mom) > 0.5 and coh > 0.6:
            regime = MarketRegime.TRENDING
        elif vol > 0.2 and abs(mom) > 0.35:
            regime = MarketRegime.BREAKOUT
        elif brd > 0.7 or brd < 0.3:
            regime = MarketRegime.REVERSAL
        else:
            regime = MarketRegime.RANGING
        return trend, regime

    def _confidence(self, coherence: float, vol: float, breadth: float) -> float:
        return max(
            0.0,
            min(
                1.0,
                0.55 * coherence
                + 0.25 * abs(breadth - 0.5) * 2
                + 0.20 * (1.0 - min(vol, 1.0)),
            ),
        )

    # analysis
    def analyze(self) -> AnalysisSnapshot:
        feats = self._features()
        se = se41_signals() or {}
        try:
            _ = se41_numeric(
                M_t=se.get("coherence", 0.5),
                DNA_states=[1.0, feats["realized_vol"], feats["breadth"], 1.1],
                harmonic_patterns=[
                    1.0,
                    1.1,
                    feats["momentum"],
                    feats["avg_depth_score"],
                    1.2,
                ],
            )
        except Exception:
            pass
        coherence = float(se.get("coherence", 0.5))
        risk = float(se.get("risk", 0.25))
        unc = float(se.get("uncertainty", 0.2))
        macro_risk = 0.5
        if self._macro:
            vix = float(self._macro.vix or 18.0)
            liq = float(self._macro.liquidity_proxy or 0.5)
            macro_risk = max(0.0, min(1.0, (vix / 40.0) * 0.7 + (1.0 - liq) * 0.3))
        trend, regime = self._trend_regime(feats, se)
        confidence = self._confidence(
            coherence, feats["realized_vol"], feats["breadth"]
        )
        snap = AnalysisSnapshot(
            ts=datetime.now(),
            symbols_covered=feats["symbols_covered"],
            avg_price=feats["avg_price"],
            total_volume=feats["total_volume"],
            realized_vol=feats["realized_vol"],
            momentum=feats["momentum"],
            breadth=feats["breadth"],
            avg_spread_bp=feats["avg_spread_bp"],
            avg_depth_score=feats["avg_depth_score"],
            macro_risk=macro_risk,
            coherence=coherence,
            confidence=confidence,
            trend=trend,
            regime=regime,
            se41_brief={
                "coherence": coherence,
                "risk": risk,
                "uncertainty": unc,
                "mirror_consistency": float(se.get("mirror_consistency", 0.5)),
                "ethos_min": min(
                    float(se.get("ethos", {}).get("authenticity", 0.0)),
                    float(se.get("ethos", {}).get("integrity", 0.0)),
                    float(se.get("ethos", {}).get("responsibility", 0.0)),
                    float(se.get("ethos", {}).get("enrichment", 0.0)),
                ),
            },
        )
        self._journal(
            {
                "type": "snapshot",
                "snapshot": _snap_dict(snap),
                "ts": snap.ts.isoformat(),
            }
        )
        return snap

    # insights
    def generate_insights(
        self, snapshot: AnalysisSnapshot, max_n: Optional[int] = None
    ) -> List[IntelligenceInsight]:
        n = max_n or self.cfg.max_insights
        insights: List[IntelligenceInsight] = []
        insights.extend(self._trend_insights(snapshot))
        insights.extend(self._risk_insights(snapshot))
        insights.extend(self._opportunity_insights(snapshot))
        insights.extend(self._macro_insights(snapshot))
        for ins in insights:
            try:
                x = se41_numeric(
                    DNA_states=[1.0, snapshot.coherence, snapshot.breadth, 1.1],
                    harmonic_patterns=[
                        1.0,
                        snapshot.realized_vol,
                        snapshot.momentum,
                        1.15,
                    ],
                )
                ins.symbolic_strength = max(0.0, min(1.0, abs(float(x)) / 50.0))
            except Exception:
                ins.symbolic_strength = max(
                    0.0, min(1.0, 0.5 * snapshot.coherence + 0.25 * snapshot.confidence)
                )
            ins.quantum_probability = min(
                1.0, ins.confidence * (0.95 + 0.1 * random.random())
            )
        insights.sort(key=lambda z: z.confidence * z.quantum_probability, reverse=True)
        top = insights[:n]
        self._journal(
            {
                "type": "insights",
                "count": len(top),
                "insights": [_ins_dict(i) for i in top],
                "ts": datetime.now().isoformat(),
            }
        )
        return top

    def _trend_insights(self, s: AnalysisSnapshot) -> List[IntelligenceInsight]:
        out: List[IntelligenceInsight] = []
        if s.trend == MarketTrend.STRONG_BULLISH and s.coherence > 0.8:
            out.append(
                IntelligenceInsight(
                    insight_id=_iid("trend_bullish"),
                    category="trend",
                    title="Strong Bullish Trend",
                    description="Coherent momentum with strong breadth suggests up-trend continuation.",
                    confidence=s.confidence,
                    impact="high",
                    timeframe="medium",
                )
            )
        elif s.trend == MarketTrend.STRONG_BEARISH and s.coherence > 0.8:
            out.append(
                IntelligenceInsight(
                    insight_id=_iid("trend_bearish"),
                    category="trend",
                    title="Strong Bearish Trend",
                    description="Coherent negative momentum; defensive posture warranted.",
                    confidence=s.confidence,
                    impact="high",
                    timeframe="medium",
                )
            )
        elif s.trend == MarketTrend.VOLATILE and s.realized_vol > self.cfg.vol_high:
            out.append(
                IntelligenceInsight(
                    insight_id=_iid("trend_vol"),
                    category="trend",
                    title="High Volatility Regime",
                    description="Elevated realized volatility; prefer smaller sizing and wider stops.",
                    confidence=s.confidence,
                    impact="medium",
                    timeframe="short",
                )
            )
        return out

    def _risk_insights(self, s: AnalysisSnapshot) -> List[IntelligenceInsight]:
        out: List[IntelligenceInsight] = []
        if (
            s.regime in (MarketRegime.CRISIS, MarketRegime.HIGH_VOLATILITY)
            and s.se41_brief["risk"] > 0.4
        ):
            out.append(
                IntelligenceInsight(
                    insight_id=_iid("risk_high"),
                    category="risk",
                    title="Elevated Systemic Risk",
                    description="Crisis/high-vol regime and SE41 risk elevated; reduce leverage, increase buffers.",
                    confidence=min(1.0, 0.6 + 0.4 * s.se41_brief["risk"]),
                    impact="high",
                    timeframe="short",
                )
            )
        if s.macro_risk > 0.6:
            out.append(
                IntelligenceInsight(
                    insight_id=_iid("risk_macro"),
                    category="risk",
                    title="Macro Risk Elevated",
                    description="Macro proxies indicate heightened risk; consider hedge overlays.",
                    confidence=0.6 + 0.3 * min(1.0, s.macro_risk),
                    impact="medium",
                    timeframe="short",
                )
            )
        return out

    def _opportunity_insights(self, s: AnalysisSnapshot) -> List[IntelligenceInsight]:
        out: List[IntelligenceInsight] = []
        if (
            s.trend in (MarketTrend.BULLISH, MarketTrend.STRONG_BULLISH)
            and s.confidence > 0.6
        ):
            allow, why = ethos_decision(
                {
                    "id": _iid("opp_increase"),
                    "purpose": "suggest_exposure_increase",
                    "amount": 1.0,
                    "currency": "NOM",
                    "tags": ["opportunity", "exposure", "increase"],
                }
            )
            if allow != "deny":
                out.append(
                    IntelligenceInsight(
                        insight_id=_iid("opp_trend_up"),
                        category="opportunity",
                        title="Momentum Continuation (Coherent)",
                        description="Moderately increase exposure to quality longs; keep risk caps active.",
                        confidence=min(1.0, 0.6 + 0.4 * s.coherence),
                        impact="medium",
                        timeframe="short",
                    )
                )
            else:
                out.append(
                    IntelligenceInsight(
                        insight_id=_iid("opp_monitor_up"),
                        category="opportunity",
                        title="Monitor Coherent Up-trend",
                        description="Setup quality long candidates watchlist; deploy only after explicit approval.",
                        confidence=0.55 + 0.35 * s.coherence,
                        impact="low",
                        timeframe="short",
                    )
                )
        if s.regime == MarketRegime.BREAKOUT and abs(s.momentum) > 0.35:
            out.append(
                IntelligenceInsight(
                    insight_id=_iid("opp_breakout"),
                    category="opportunity",
                    title="Breakout Conditions",
                    description="Breakout signals present; favor liquid names with tight spreads.",
                    confidence=0.6 + 0.3 * min(1.0, abs(s.momentum)),
                    impact="medium",
                    timeframe="short",
                )
            )
        return out

    def _macro_insights(self, s: AnalysisSnapshot) -> List[IntelligenceInsight]:
        out: List[IntelligenceInsight] = []
        if self._macro:
            if self._macro.vix > 28:
                out.append(
                    IntelligenceInsight(
                        insight_id=_iid("macro_vix"),
                        category="macro",
                        title="VIX Elevated",
                        description="Volatility index elevated; consider hedge overlay, avoid illiquid exposures.",
                        confidence=0.7,
                        impact="high",
                        timeframe="short",
                    )
                )
            if self._macro.cpi_yoy > 0.04:
                out.append(
                    IntelligenceInsight(
                        insight_id=_iid("macro_infl"),
                        category="macro",
                        title="Inflationary Pressure",
                        description="CPI YoY above comfort; favor pricing power & inflation-resilient sectors.",
                        confidence=0.6,
                        impact="medium",
                        timeframe="medium",
                    )
                )
        return out

    # journal
    def _journal(self, obj: Dict[str, Any]) -> None:
        try:
            with self._journal_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(obj) + "\n")
        except Exception:
            pass


def _iid(prefix: str) -> str:
    return f"{prefix}_{int(time.time()*1000)}_{random.randint(1000,9999)}"


def _snap_dict(s: AnalysisSnapshot) -> Dict[str, Any]:
    return {
        "ts": s.ts.isoformat(),
        "symbols_covered": s.symbols_covered,
        "avg_price": s.avg_price,
        "total_volume": s.total_volume,
        "realized_vol": s.realized_vol,
        "momentum": s.momentum,
        "breadth": s.breadth,
        "avg_spread_bp": s.avg_spread_bp,
        "avg_depth_score": s.avg_depth_score,
        "macro_risk": s.macro_risk,
        "coherence": s.coherence,
        "confidence": s.confidence,
        "trend": s.trend.value,
        "regime": s.regime.value,
        "se41": s.se41_brief,
    }


def _ins_dict(i: IntelligenceInsight) -> Dict[str, Any]:
    return {
        "id": i.insight_id,
        "category": i.category,
        "title": i.title,
        "description": i.description,
        "symbols": i.symbols,
        "confidence": i.confidence,
        "impact": i.impact,
        "timeframe": i.timeframe,
        "symbolic_strength": i.symbolic_strength,
        "quantum_probability": i.quantum_probability,
        "ts": i.timestamp.isoformat(),
    }


def create_market_analyzer(**kwargs) -> MarketIntelligenceAnalyzer:
    return MarketIntelligenceAnalyzer(**kwargs)


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    print("=" * 70)
    print(
        "EidollonaONE Market Intelligence Analyzer v4.1+ — coherent • ethical • auditable"
    )
    print("=" * 70)
    mia = create_market_analyzer()
    now = datetime.now()
    for k in range(500):
        mia.ingest_tick(
            MarketTick(
                symbol="EIDO",
                price=100 + math.sin(k / 50) * 2 + random.uniform(-0.3, 0.3),
                volume=random.randint(500, 2500),
                timestamp=now - timedelta(seconds=500 - k),
                bid=99.9,
                ask=100.1,
                spread=0.2,
                depth_bid=random.uniform(2e3, 6e3),
                depth_ask=random.uniform(2e3, 6e3),
            )
        )
    mia.set_macro(
        MacroSnapshot(timestamp=now, vix=22.5, liquidity_proxy=0.55, growth_proxy=0.52)
    )
    snap = mia.analyze()
    print("Snapshot:", json.dumps(_snap_dict(snap), indent=2))
    ins = mia.generate_insights(snap)
    print(f"\nTop {len(ins)} insights:")
    for x in ins:
        print(
            f" - [{x.category}] {x.title} (conf={x.confidence:.2f}, q={x.quantum_probability:.2f})"
        )

__all__ = [
    "MarketIntelligenceAnalyzer",
    "create_market_analyzer",
    "MarketIntelConfig",
    "MarketTick",
    "NewsEvent",
    "MacroSnapshot",
    "AnalysisSnapshot",
    "IntelligenceInsight",
]
