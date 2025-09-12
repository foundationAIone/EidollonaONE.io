# trading_engine/compliance_auditor.py
# ============================================================
# EidollonaONE Compliance Auditor — SE41 v4.1+ aligned
# Consumes SymbolicEquation41 via shared helper to:
#  - read SE41Signals safely (se41_signals())
#  - compute symbolic coherence for compliance review
#  - gate enforcement ethically (ethos_decision)
# ============================================================

from __future__ import annotations

# Standard library imports
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# v4.1 core + shared context (kept for optional local evaluation)
from symbolic_core.symbolic_equation41 import SymbolicEquation41
from symbolic_core.se41_context import assemble_se41_context

# Shared trading helper (centralized; no in-file helper injection)
from trading.helpers.se41_trading_gate import se41_signals, ethos_decision

# Optional: legal framework & trade components
try:
    from legal_framework.legal_framework_engine import LegalFrameworkEngine

    LEGAL_FRAMEWORK_AVAILABLE = True
except Exception:
    LEGAL_FRAMEWORK_AVAILABLE = False

try:
    from trading_engine.ai_trade_executor import TradeType, MarketType, RiskLevel

    TRADE_COMPONENTS_AVAILABLE = True
except Exception:
    # Provide lightweight fallbacks so typing of dataclass fields still works
    class TradeType(Enum):
        MARKET = "market"

    class MarketType(Enum):
        SPOT = "spot"

    class RiskLevel(Enum):
        LOW = "low"

    TRADE_COMPONENTS_AVAILABLE = False


"""
⚖️ EidollonaONE Compliance Auditor v4.1+

v4.1 upgrade:
- Moves from raw numeric "symbolic" calls to true SE41Signals consumption.
- Coherence = f(coherence, mirror_consistency, ethos_min) damped by risk/uncertainty.
- Enforcement recommendations are *ethos-gated*; every action must pass Four-Pillars.
- Safer architecture: single shared helper → fewer regressions, easier audits.

Purpose: Comprehensive trading compliance & regulatory oversight, harmonized
with the Symbolic Equation v4.1+ signals and the Four Pillars ethos.
"""


# ----------------------------- Enums & Models -----------------------------


class ComplianceLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    VIOLATION = "violation"
    CRITICAL = "critical"
    REGULATORY = "regulatory"


class ComplianceType(Enum):
    POSITION_LIMITS = "position_limits"
    CONCENTRATION_RISK = "concentration_risk"
    TRADING_HOURS = "trading_hours"
    MARKET_MANIPULATION = "market_manipulation"
    INSIDER_TRADING = "insider_trading"
    WASH_TRADING = "wash_trading"
    LEVERAGE_LIMITS = "leverage_limits"
    RISK_LIMITS = "risk_limits"
    REGULATORY_REPORTING = "regulatory_reporting"
    CLIENT_SUITABILITY = "client_suitability"
    BEST_EXECUTION = "best_execution"
    RECORD_KEEPING = "record_keeping"


class AuditStatus(Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    ARCHIVED = "archived"


@dataclass
class ComplianceRule:
    rule_id: str
    name: str
    compliance_type: ComplianceType
    description: str

    # Parameters
    threshold_value: Optional[float] = None  # absolute / percent / ratio value
    threshold_type: str = "absolute"  # absolute | percentage | ratio
    time_window: Optional[int] = None  # seconds
    market_types: List[MarketType] = field(default_factory=list)

    # State
    is_active: bool = True
    severity_level: ComplianceLevel = ComplianceLevel.WARNING
    auto_enforce: bool = False

    created_time: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    violation_count: int = 0
    last_violation: Optional[datetime] = None

    # Symbolic metrics (last validation)
    symbolic_coherence: float = 0.0
    quantum_reliability: float = 0.0
    consciousness_alignment: float = 0.0


@dataclass
class ComplianceViolation:
    violation_id: str
    rule_id: str
    rule_name: str
    compliance_type: ComplianceType
    severity_level: ComplianceLevel

    description: str
    actual_value: Optional[float] = None
    threshold_value: Optional[float] = None
    violation_amount: Optional[float] = None

    symbol: Optional[str] = None
    order_id: Optional[str] = None
    position_id: Optional[str] = None
    account_id: Optional[str] = None

    status: AuditStatus = AuditStatus.PENDING
    detected_time: datetime = field(default_factory=datetime.now)
    resolved_time: Optional[datetime] = None
    resolution_notes: str = ""

    risk_score: float = 0.0
    impact_assessment: str = ""
    recommended_action: str = ""

    symbolic_verification: float = 0.0
    quantum_certainty: float = 0.0
    consciousness_ethics_score: float = 0.0


@dataclass
class AuditReport:
    report_id: str
    report_type: str
    period_start: datetime
    period_end: datetime

    total_transactions: int = 0
    total_violations: int = 0
    critical_violations: int = 0
    regulatory_violations: int = 0

    overall_compliance_score: float = 0.0
    risk_adjusted_score: float = 0.0
    trend_analysis: str = ""

    violations_by_type: Dict[str, int] = field(default_factory=dict)
    violations_by_severity: Dict[str, int] = field(default_factory=dict)

    improvement_recommendations: List[str] = field(default_factory=list)
    priority_actions: List[str] = field(default_factory=list)

    symbolic_compliance_coherence: float = 0.0
    quantum_audit_reliability: float = 0.0
    consciousness_ethical_alignment: float = 0.0


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
    Coherence scalar [0..1] for compliance:
    blend of coherence + mirror_consistency + ethos_min, damped by risk + uncertainty.
    """
    if not sig:
        return 0.0
    coh = float(sig.get("coherence", 0.0))
    mc = float(sig.get("mirror_consistency", 0.0))
    me = _min_ethos(sig)
    risk = float(sig.get("risk", 0.2))
    unc = float(sig.get("uncertainty", 0.2))
    raw = 0.50 * coh + 0.30 * mc + 0.20 * me
    damp = max(0.35, 1.0 - 0.55 * (risk + unc))
    return max(0.0, min(1.0, raw * damp))


# ----------------------------- Symbolic Validator -----------------------------


class SymbolicComplianceValidator:
    """SE41-based compliance coherence validator."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.SymbolicComplianceValidator")
        self._se41 = SymbolicEquation41()

    def validate_compliance_coherence(
        self,
        rule: ComplianceRule,
        violation_data: Dict[str, Any],
        trading_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Pull SE41Signals (prefer helper → live signals; fallback to local evaluate),
        compute a bounded coherence scalar, and return a structured assessment.
        """
        try:
            sig = se41_signals()
            if not sig:
                # Safe fallback: single local evaluation with a minimal context
                ctx = assemble_se41_context()
                s = self._se41.evaluate(ctx)
                sig = getattr(s, "__dict__", {}) if hasattr(s, "__dict__") else {}

            coherence_score = _symbolic_coherence(sig)
            rule.symbolic_coherence = coherence_score

            assessment = self._assess(
                rule, violation_data, trading_context, coherence_score
            )

            return {
                "valid": True,
                "coherence_score": coherence_score,
                "signals": sig,
                "compliance_assessment": assessment,
                "enforcement_recommendation": (coherence_score >= 0.7),
                "validation_timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error("Compliance validation failed: %s", e)
            return {"valid": False, "coherence_score": 0.0, "error": str(e)}

    # ---- internal helpers ----

    def _severity_factor(self, sev: ComplianceLevel) -> float:
        return {
            ComplianceLevel.INFO: 0.2,
            ComplianceLevel.WARNING: 0.4,
            ComplianceLevel.VIOLATION: 0.6,
            ComplianceLevel.CRITICAL: 0.8,
            ComplianceLevel.REGULATORY: 1.0,
        }.get(sev, 0.5)

    def _assess(
        self,
        rule: ComplianceRule,
        violation_data: Dict[str, Any],
        trading_context: Dict[str, Any],
        coherence_score: float,
    ) -> str:
        """
        Provide an interpretable label that compliance workflows can route on.
        """
        try:
            sev = rule.severity_level
            ratio = float(violation_data.get("threshold_ratio", 1.0))
            if coherence_score >= 0.9 and sev in (
                ComplianceLevel.CRITICAL,
                ComplianceLevel.REGULATORY,
            ):
                return "critical_compliance_breach"
            if coherence_score >= 0.8 and ratio > 1.5:
                return "significant_violation"
            if coherence_score >= 0.7:
                return "moderate_violation"
            if coherence_score >= 0.5:
                return "minor_violation"
            return "potential_false_positive"
        except Exception as e:
            self.logger.error("Assessment failed: %s", e)
            return "assessment_error"


# ----------------------------- Quantum Risk (simplified) -----------------------------


class QuantumRiskAssessment:
    """Quantum-enhanced risk assessment for compliance (simplified placeholder)."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.QuantumRiskAssessment")

    def assess_compliance_risk(
        self,
        violation: ComplianceViolation,
        trading_context: Dict[str, Any],
        historical_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        try:
            quantum_uncertainty = random.uniform(0.9, 1.1)
            risk_coherence = random.uniform(0.8, 1.0)

            severity_risk = self._severity_risk(violation.severity_level)
            frequency_risk = self._frequency_risk(historical_data)
            impact_risk = self._impact_risk(violation, trading_context)
            regulatory_risk = self._reg_risk(violation.compliance_type)

            base = (
                0.3 * severity_risk
                + 0.2 * frequency_risk
                + 0.3 * impact_risk
                + 0.2 * regulatory_risk
            )
            score = min(1.0, base * quantum_uncertainty * risk_coherence)
            violation.risk_score = score

            category = (
                "critical"
                if score >= 0.8
                else (
                    "high"
                    if score >= 0.6
                    else (
                        "moderate"
                        if score >= 0.4
                        else "low" if score >= 0.2 else "minimal"
                    )
                )
            )

            recs = self._mitigation(violation, score)
            return {
                "risk_score": score,
                "risk_category": category,
                "quantum_uncertainty": quantum_uncertainty,
                "mitigation_recommendations": recs,
                "assessment_timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error("Compliance risk assessment failed: %s", e)
            return {"risk_score": 0.5, "risk_category": "moderate"}

    # -- inner calculators --

    def _severity_risk(self, sev: ComplianceLevel) -> float:
        return {
            ComplianceLevel.INFO: 0.1,
            ComplianceLevel.WARNING: 0.3,
            ComplianceLevel.VIOLATION: 0.6,
            ComplianceLevel.CRITICAL: 0.8,
            ComplianceLevel.REGULATORY: 1.0,
        }.get(sev, 0.5)

    def _frequency_risk(self, hist: Dict[str, Any]) -> float:
        rv = int(hist.get("recent_violations", 0))
        if rv == 0:
            return 0.1
        if rv <= 2:
            return 0.3
        if rv <= 5:
            return 0.6
        return 0.9

    def _impact_risk(self, v: ComplianceViolation, ctx: Dict[str, Any]) -> float:
        amount = float(v.violation_amount or 0.0)
        pv = float(ctx.get("portfolio_value", 100_000.0))
        if pv <= 0:
            return 0.4
        ratio = amount / pv
        if ratio > 0.10:
            return 0.9
        if ratio > 0.05:
            return 0.7
        if ratio > 0.01:
            return 0.5
        return 0.3

    def _reg_risk(self, t: ComplianceType) -> float:
        return {
            ComplianceType.MARKET_MANIPULATION: 1.0,
            ComplianceType.INSIDER_TRADING: 1.0,
            ComplianceType.REGULATORY_REPORTING: 0.9,
            ComplianceType.POSITION_LIMITS: 0.8,
            ComplianceType.LEVERAGE_LIMITS: 0.7,
            ComplianceType.CONCENTRATION_RISK: 0.6,
            ComplianceType.TRADING_HOURS: 0.4,
            ComplianceType.BEST_EXECUTION: 0.5,
            ComplianceType.WASH_TRADING: 0.8,
            ComplianceType.RISK_LIMITS: 0.6,
            ComplianceType.CLIENT_SUITABILITY: 0.7,
            ComplianceType.RECORD_KEEPING: 0.5,
        }.get(t, 0.5)

    def _mitigation(self, v: ComplianceViolation, score: float) -> List[str]:
        recs: List[str] = []
        if score >= 0.8:
            recs += [
                "immediate_trading_halt",
                "senior_management_notification",
                "regulatory_disclosure_preparation",
                "legal_counsel_consultation",
            ]
        elif score >= 0.6:
            recs += [
                "position_size_reduction",
                "enhanced_monitoring",
                "risk_committee_review",
                "compliance_procedure_review",
            ]
        elif score >= 0.4:
            recs += [
                "increased_oversight",
                "system_parameter_adjustment",
                "staff_training_review",
            ]
        # Type-specific nudge
        if v.compliance_type == ComplianceType.POSITION_LIMITS:
            recs.append("implement_position_size_controls")
        elif v.compliance_type == ComplianceType.CONCENTRATION_RISK:
            recs.append("diversification_requirements")
        elif v.compliance_type == ComplianceType.LEVERAGE_LIMITS:
            recs.append("leverage_reduction_protocol")
        return recs


# ----------------------------- Compliance Auditor -----------------------------


class ComplianceAuditor:
    """
    EidollonaONE Compliance Auditor — SE41 v4.1+
    Symbolic (SE41) validation, quantum risk lens, ethos-gated enforcement.
    """

    def __init__(self, auditor_directory: Optional[str] = None) -> None:
        self.logger = logging.getLogger(f"{__name__}.ComplianceAuditor")
        self.auditor_directory = Path(auditor_directory or "compliance_auditor_data")
        self.auditor_directory.mkdir(exist_ok=True)

        self.validator = SymbolicComplianceValidator()
        self.risk_assessor = QuantumRiskAssessment()

        self.compliance_rules: Dict[str, ComplianceRule] = {}
        self.violations: Dict[str, ComplianceViolation] = {}
        self.audit_reports: Dict[str, AuditReport] = {}

        self.legal_framework = None
        if LEGAL_FRAMEWORK_AVAILABLE:
            try:
                self.legal_framework = LegalFrameworkEngine()
            except Exception as e:
                self.logger.warning("Legal framework not available: %s", e)

        self.monitoring_enabled = True
        self.auto_enforcement = False
        self.audit_interval = 3600
        self.max_violations_per_day = 100

        self._initialize_default_rules()

        self.logger.info("EidollonaONE Compliance Auditor v4.1+ initialized")
        self.logger.info(
            "Symbolic Validation: ✅ | Quantum Risk: ✅ | Legal: %s",
            "✅" if self.legal_framework else "❌",
        )
        self.logger.info("Loaded Rules: %d", len(self.compliance_rules))

    # --------- public API ---------

    def add_violation(
        self, violation: ComplianceViolation, trading_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Register a violation, run symbolic + quantum analyses, and (optionally)
        ethos-gate the enforcement recommendation.
        """
        self.violations[violation.violation_id] = violation
        rule = self.compliance_rules.get(violation.rule_id)
        if not rule:
            return {"ok": False, "error": "rule_not_found"}

        # symbolic coherence
        vdata = {
            "threshold_ratio": self._threshold_ratio(violation),
            "violation_time": violation.detected_time,
            "detection_time": datetime.now(),
        }
        val = self.validator.validate_compliance_coherence(rule, vdata, trading_context)
        violation.symbolic_verification = float(val.get("coherence_score", 0.0))

        # quantum lens
        q = self.risk_assessor.assess_compliance_risk(
            violation,
            trading_context,
            {
                "recent_violations": rule.violation_count,
                "total_violations": rule.violation_count,
            },
        )

        # ethos-gate an action if auto enforcement is enabled
        action = None
        if self.auto_enforcement:
            tx = {
                "id": f"enforce_{violation.violation_id}",
                "purpose": "compliance_enforcement",
                "amount": float(violation.violation_amount or 0.0),
                "currency": "USD",
                "tags": ["compliance", "enforcement"],
            }
            decision, reason = ethos_decision(tx)
            action = {"ethos_decision": decision, "reason": reason}

        # update rule counters
        rule.violation_count += 1
        rule.last_violation = datetime.now()

        return {
            "ok": True,
            "violation_id": violation.violation_id,
            "symbolic": val,
            "quantum": q,
            "ethos_action": action,
        }

    def build_report(self, period_start: datetime, period_end: datetime) -> AuditReport:
        """
        Summarize violations within a period and compute symbolic/quantum rollups.
        """
        report = AuditReport(
            report_id=f"report_{int(time.time())}",
            report_type="periodic",
            period_start=period_start,
            period_end=period_end,
        )

        # Aggregate violations
        for v in self.violations.values():
            if not (period_start <= v.detected_time <= period_end):
                continue
            report.total_violations += 1
            report.violations_by_type[v.compliance_type.value] = (
                report.violations_by_type.get(v.compliance_type.value, 0) + 1
            )
            report.violations_by_severity[v.severity_level.value] = (
                report.violations_by_severity.get(v.severity_level.value, 0) + 1
            )
            if v.severity_level == ComplianceLevel.CRITICAL:
                report.critical_violations += 1
            if v.severity_level == ComplianceLevel.REGULATORY:
                report.regulatory_violations += 1

        # Symbolic rollup: prefer live signals; else local evaluate
        sig = se41_signals()
        if not sig:
            s = SymbolicEquation41().evaluate(assemble_se41_context())
            sig = getattr(s, "__dict__", {}) if hasattr(s, "__dict__") else {}

        coh = _symbolic_coherence(sig)
        report.symbolic_compliance_coherence = coh

        # Simple overall & risk-adjusted scores
        total = max(1, report.total_violations)
        severity_penalty = (
            0.1 * report.critical_violations + 0.05 * report.regulatory_violations
        )
        report.overall_compliance_score = max(
            0.0, min(1.0, 0.9 * coh - severity_penalty)
        )
        report.risk_adjusted_score = max(
            0.0,
            min(
                1.0,
                report.overall_compliance_score
                * (1.0 - 0.5 * float(sig.get("risk", 0.2))),
            ),
        )

        # Recommendations (illustrative)
        if report.critical_violations > 0:
            report.priority_actions.append("launch_immediate_root_cause_analysis")
        if report.regulatory_violations > 0:
            report.priority_actions.append(
                "prepare_regulatory_disclosure_and_remediation_plan"
            )
        if report.overall_compliance_score < 0.6:
            report.improvement_recommendations.append(
                "tighten_real_time_limits_and_alerting"
            )

        self.audit_reports[report.report_id] = report
        return report

    # --------- internal helpers ---------

    def _threshold_ratio(self, v: ComplianceViolation) -> float:
        try:
            if v.threshold_value in (None, 0):
                return 1.0
            if v.actual_value is None:
                return 1.0
            return float(v.actual_value) / float(v.threshold_value)
        except Exception:
            return 1.0

    def _initialize_default_rules(self) -> None:
        """
        Seed a minimal ruleset. Projects typically load rules from config/storage.
        """

        def _r(
            i: str,
            name: str,
            t: ComplianceType,
            desc: str,
            thr: Optional[float],
            sev: ComplianceLevel,
            auto: bool,
        ) -> ComplianceRule:
            return ComplianceRule(
                rule_id=i,
                name=name,
                compliance_type=t,
                description=desc,
                threshold_value=thr,
                severity_level=sev,
                auto_enforce=auto,
            )

        self.compliance_rules = {
            "R_POS_01": _r(
                "R_POS_01",
                "Position Limits",
                ComplianceType.POSITION_LIMITS,
                "Prevent position sizes above configured limits.",
                1_000_000.0,
                ComplianceLevel.VIOLATION,
                True,
            ),
            "R_CONC_01": _r(
                "R_CONC_01",
                "Concentration Risk",
                ComplianceType.CONCENTRATION_RISK,
                "Diversify; avoid excessive single-name concentration.",
                0.25,
                ComplianceLevel.WARNING,
                False,
            ),
            "R_LVG_01": _r(
                "R_LVG_01",
                "Leverage Limits",
                ComplianceType.LEVERAGE_LIMITS,
                "Keep leverage within approved bounds.",
                5.0,
                ComplianceLevel.CRITICAL,
                True,
            ),
        }


# ----------------------------- Factory & CLI -----------------------------


def create_compliance_auditor(**kwargs) -> ComplianceAuditor:
    return ComplianceAuditor(**kwargs)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    print("=" * 70)
    print("EidollonaONE Compliance Auditor v4.1+")
    print("Framework: Symbolic Equation v4.1+ with Ethos-Gated Enforcement")
    print("Purpose: Comprehensive Trading Compliance and Regulatory Oversight")
    print("=" * 70)
    try:
        print("\n⚖️ Initializing Compliance Auditor...")
        auditor = create_compliance_auditor()
        print("✅ Compliance Auditor initialized successfully!")
        print("🚀 Ready for comprehensive compliance monitoring!")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
