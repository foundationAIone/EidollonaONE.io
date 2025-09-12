"""Risk Management Suite

Exports:
 - VaREngine: Historical & parametric VaR + ES
 - TailRiskEngine: EVT-style tail index & severity
 - StressTester: Scenario-based portfolio stress losses
 - ComplianceEngine: Policy constraint enforcement
 - RiskAnalyzer: Composite aggregator (VaR, tail, stress, compliance)
 - RiskDashboard: Human-readable snapshot renderer
"""

from .value_at_risk import VaREngine
from .tail_risk import TailRiskEngine
from .stress_testing import StressTester, Position
from .compliance_engine import ComplianceEngine, ComplianceConfig
from .risk_analyzer import RiskAnalyzer
from .risk_dashboard import RiskDashboard

__all__ = [
    "VaREngine",
    "TailRiskEngine",
    "StressTester",
    "Position",
    "ComplianceEngine",
    "ComplianceConfig",
    "RiskAnalyzer",
    "RiskDashboard",
]
