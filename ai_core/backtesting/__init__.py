"""Backtesting & Scenario Analysis Toolkit (SE41 v4.1+ aligned)

Provides governance-aware simulation primitives:
	* historical_simulator – sequential bar replay with strategy callback
	* event_driven        – queue-based market / order / fill simulation
	* portfolio_backtest  – portfolio accounting & performance metrics
	* monte_carlo         – stochastic path generation (GBM & shocks)
	* scenario_analysis   – stress & regime shift application utilities

Design goals:
	* Deterministic reproducibility (seed control) where randomness used
	* Ethos & numeric gating for extreme leverage / turnover conditions
	* Pure-Python minimal dependency surface (numpy optional fallback)
	* Clear metrics surfaces (dict snapshots) for higher-layer ingestion
"""

from .historical_simulator import HistoricalSimulator, Bar
from .event_driven import (
    EventDrivenEngine,
    Event,
    MarketEvent,
    SignalEvent,
    OrderEvent,
    FillEvent,
)
from .portfolio_backtest import PortfolioAccount, PerformanceReport, PortfolioBacktest
from .monte_carlo import MonteCarloEngine, PathResult
from .scenario_analysis import apply_scenarios, ScenarioSpec, ScenarioResult

__all__ = [
    "HistoricalSimulator",
    "Bar",
    "EventDrivenEngine",
    "Event",
    "MarketEvent",
    "SignalEvent",
    "OrderEvent",
    "FillEvent",
    "PortfolioAccount",
    "PerformanceReport",
    "PortfolioBacktest",
    "MonteCarloEngine",
    "PathResult",
    "apply_scenarios",
    "ScenarioSpec",
    "ScenarioResult",
]
