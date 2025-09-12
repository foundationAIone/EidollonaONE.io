"""
🧾 EidollonaONE Purchase Manager v4.1+

Purpose
-------
Controls procurement (data feeds, infra, research, broker services, compliance tooling,
and other operational spend) with:
  • SE41 symbolic merit scoring (bounded numeric synthesis)
  • Ethos gating (Authenticity / Integrity / Responsibility / Enrichment)
  • Budget/risk checks and audit logs
  • Simple vendor performance learning loop

This keeps spend aligned with your Four Pillars and the same decision surface
used across trading/portfolio/compliance.

Key endpoints (programmatic)
----------------------------
PurchaseManager.submit_request(...)   -> queues a request
PurchaseManager.review_request(...)   -> returns SE41 + ethos reasoning
PurchaseManager.approve_request(...)  -> finalizes and books the spend
PurchaseManager.fulfill_request(...)  -> marks fulfilled (invoice paid/activated)
PurchaseManager.cancel_request(...)   -> cancels safely
PurchaseManager.budget_status()       -> snapshot for dashboards
"""

from __future__ import annotations

import logging
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

# --- SE41 unified imports ----------------------------------------------------
from symbolic_core.symbolic_equation41 import SymbolicEquation41, SE41Signals
from trading.helpers.se41_trading_gate import (
    ethos_decision,  # Four Pillars gate → allow/hold/deny + reasons
    se41_numeric,  # bounded numeric synthesis helper used across v4.1 modules
)

# --- Adjacent fallbacks ------------------------------------------------------
try:

    RISK_ENUM_AVAILABLE = True
except Exception:
    RISK_ENUM_AVAILABLE = False

# -----------------------------------------------------------------------------


class PurchaseType(Enum):
    DATA_FEED = "data_feed"
    RESEARCH = "research"
    BROKER_SERVICE = "broker_service"
    CLOUD_INFRA = "cloud_infra"
    COMPLIANCE_TOOL = "compliance_tool"
    SECURITY_TOOL = "security_tool"
    HARDWARE = "hardware"
    OTHER = "other"


class PurchasePriority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    DEFERRED = 5


class PurchaseStatus(Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DENIED = "denied"
    ON_HOLD = "on_hold"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


@dataclass
class VendorProfile:
    vendor_id: str
    name: str
    category: PurchaseType
    reliability: float = 0.75  # 0..1 (SLA, uptime, support response)
    integrity: float = 0.85  # 0..1 (contract clarity, pricing honesty)
    enrichment: float = 0.80  # 0..1 (value delivered for mission)
    last_review: Optional[datetime] = None
    active: bool = True


@dataclass
class BudgetSnapshot:
    as_of: datetime
    fiscal_year: str
    spend_limit: float
    committed: float
    available: float
    safety_buffer: float  # allocation reserved for emergencies (0..1 of spend_limit)


@dataclass
class PurchaseRequest:
    request_id: str
    title: str
    description: str
    vendor_id: str
    purchase_type: PurchaseType
    priority: PurchasePriority
    cost: float  # total cost (period or one-time)
    term_months: int = 1
    is_recurring: bool = False

    # Attachments / context
    business_value_score: float = 0.0  # (0..1) rough pre-assessment
    operational_need_score: float = 0.0  # (0..1) outage risk mitigation, etc.
    risk_mitigation_score: float = 0.0  # (0..1) improves security/compliance
    alignment_note: str = ""

    # Timestamps / status
    submitted_at: datetime = field(default_factory=datetime.now)
    status: PurchaseStatus = PurchaseStatus.SUBMITTED

    # SE41 / ethos
    se41: Optional[SE41Signals] = None
    se41_numeric_score: float = 0.0
    ethos_gate: str = "undecided"  # allow/hold/deny
    ethos_reasons: List[str] = field(default_factory=list)


@dataclass
class PurchaseDecision:
    decision_id: str
    request_id: str
    status: PurchaseStatus
    approver: str
    decided_at: datetime = field(default_factory=datetime.now)
    reasons: List[str] = field(default_factory=list)
    se41_snapshot: Optional[Dict[str, Any]] = None
    budget_snapshot: Optional[BudgetSnapshot] = None


@dataclass
class PurchaseOrder:
    po_id: str
    request_id: str
    vendor_id: str
    cost: float
    currency: str = "USD"
    created_at: datetime = field(default_factory=datetime.now)
    activated_at: Optional[datetime] = None
    invoice_due_at: Optional[datetime] = None
    status: PurchaseStatus = PurchaseStatus.APPROVED
    terms: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""


class SymbolicPurchaseValidator:
    """
    Bounded SE41 numeric synthesis for purchases.
    Combines: business value, operational need, risk mitigation, vendor traits, budget pressure,
    and priority → a single *coherence merit* score in [0..1].
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.SymbolicPurchaseValidator")
        self._se41 = SymbolicEquation41()

    def evaluate(
        self, req: PurchaseRequest, vendor: VendorProfile, budget: BudgetSnapshot
    ) -> Dict[str, Any]:
        try:
            # Normalize inputs
            value = max(0.0, min(req.business_value_score, 1.0))
            need = max(0.0, min(req.operational_need_score, 1.0))
            mitigate = max(0.0, min(req.risk_mitigation_score, 1.0))
            v_rel = max(0.0, min(vendor.reliability, 1.0))
            v_int = max(0.0, min(vendor.integrity, 1.0))
            v_enr = max(0.0, min(vendor.enrichment, 1.0))

            # Budget pressure: higher pressure reduces M_t
            pressure = 1.0 - max(
                0.0, min(budget.available / max(budget.spend_limit, 1.0), 1.0)
            )
            # Priority: CRITICAL(1)..DEFERRED(5) → urgency 1..0
            urgency = 1.0 - (req.priority.value - 1) / 4.0

            numeric = se41_numeric(
                # Mean field: available headroom and urgency improve manifestation
                M_t=max(0.05, (1.0 - pressure) * 0.6 + urgency * 0.4),
                DNA_states=[
                    1.0,
                    value,
                    need,
                    mitigate,
                    v_rel,
                    v_int,
                    v_enr,
                    urgency,
                    1.1,
                ],
                harmonic_patterns=[
                    1.0,
                    1.2,
                    value,
                    need,
                    mitigate,
                    (1.0 - pressure),
                    urgency,
                    v_rel,
                    v_int,
                    v_enr,
                    1.3,
                ],
            )

            ok = (
                isinstance(numeric, (int, float))
                and math.isfinite(numeric)
                and 0.001 < abs(numeric) < 1000.0
            )
            if not ok:
                return {"valid": False, "score": 0.0}

            # Scale numeric into a 0..1 merit
            merit = min(abs(float(numeric)) / 65.0, 1.0)

            # Build SE41Signals quickly (or call se41_signals if you want a heavier packet)
            # Here we mirror a minimal set for dashboards.
            quick_signals: Dict[str, Any] = {
                "coherence": round(merit, 4),
                "risk": round(pressure, 4),
                "impetus": round(urgency * merit, 4),
                "ethos": {
                    "authenticity": round(v_int * 0.9 + 0.1 * value, 4),
                    "integrity": round(v_int, 4),
                    "responsibility": round(mitigate, 4),
                    "enrichment": round(v_enr * value, 4),
                },
                "explain": "purchase_merit",
            }

            self.logger.info(
                f"[SE41] purchase merit={merit:.3f} pressure={pressure:.3f} urgency={urgency:.3f}"
            )
            return {"valid": True, "score": merit, "signals": quick_signals}

        except Exception as e:
            self.logger.error(f"Purchase evaluation failed: {e}")
            return {"valid": False, "score": 0.0, "error": str(e)}


class PurchaseManager:
    """
    EidollonaONE Purchase Manager (SE41 v4.1+)

    • Submits & reviews purchase requests
    • Applies SE41 bounded merit + Ethos gate
    • Keeps budgets, POs and audit trail coherent and reproducible
    """

    def __init__(
        self,
        fiscal_year: Optional[str] = None,
        spend_limit: float = 250_000.0,
        safety_buffer: float = 0.10,
        storage_dir: Optional[str] = None,
    ):
        self.logger = logging.getLogger(f"{__name__}.PurchaseManager")

        self._dir = Path(storage_dir or "purchase_manager_data")
        self._dir.mkdir(exist_ok=True)

        fy = fiscal_year or f"FY{datetime.now().year}"
        self._budget = BudgetSnapshot(
            as_of=datetime.now(),
            fiscal_year=fy,
            spend_limit=float(spend_limit),
            committed=0.0,
            available=float(spend_limit),
            safety_buffer=float(safety_buffer),
        )

        self._vendors: Dict[str, VendorProfile] = {}
        self._requests: Dict[str, PurchaseRequest] = {}
        self._decisions: Dict[str, PurchaseDecision] = {}
        self._pos: Dict[str, PurchaseOrder] = {}

        self._validator = SymbolicPurchaseValidator()

        self.logger.info(
            f"Purchase Manager v4.1+ ready | {fy} limit=${spend_limit:,.0f} buffer={safety_buffer:.0%}"
        )

    # ---------------- vendor admin ----------------

    def register_vendor(
        self,
        name: str,
        category: PurchaseType,
        reliability: float = 0.75,
        integrity: float = 0.85,
        enrichment: float = 0.80,
    ) -> VendorProfile:
        vid = f"ven_{uuid.uuid4().hex[:10]}"
        vp = VendorProfile(
            vendor_id=vid,
            name=name,
            category=category,
            reliability=reliability,
            integrity=integrity,
            enrichment=enrichment,
        )
        self._vendors[vid] = vp
        return vp

    def update_vendor_review(
        self,
        vendor_id: str,
        reliability: Optional[float] = None,
        integrity: Optional[float] = None,
        enrichment: Optional[float] = None,
        active: Optional[bool] = None,
    ) -> Optional[VendorProfile]:
        v = self._vendors.get(vendor_id)
        if not v:
            return None
        if reliability is not None:
            v.reliability = max(0.0, min(reliability, 1.0))
        if integrity is not None:
            v.integrity = max(0.0, min(integrity, 1.0))
        if enrichment is not None:
            v.enrichment = max(0.0, min(enrichment, 1.0))
        if active is not None:
            v.active = bool(active)
        v.last_review = datetime.now()
        return v

    # ---------------- purchase flow --------------

    def submit_request(
        self,
        title: str,
        description: str,
        vendor_id: str,
        ptype: PurchaseType,
        priority: PurchasePriority,
        cost: float,
        term_months: int = 1,
        is_recurring: bool = False,
        business_value: float = 0.0,
        operational_need: float = 0.0,
        risk_mitigation: float = 0.0,
        alignment_note: str = "",
    ) -> PurchaseRequest:
        if vendor_id not in self._vendors:
            raise ValueError("Vendor not registered")
        rid = f"req_{uuid.uuid4().hex[:10]}"
        req = PurchaseRequest(
            request_id=rid,
            title=title,
            description=description,
            vendor_id=vendor_id,
            purchase_type=ptype,
            priority=priority,
            cost=float(cost),
            term_months=int(term_months),
            is_recurring=bool(is_recurring),
            business_value_score=business_value,
            operational_need_score=operational_need,
            risk_mitigation_score=risk_mitigation,
            alignment_note=alignment_note,
        )
        self._requests[rid] = req
        self.logger.info(
            f"[Submit] {rid} {title} ${cost:,.2f} ({ptype.value}, {priority.name})"
        )
        return req

    def review_request(self, request_id: str) -> Dict[str, Any]:
        req = self._requests.get(request_id)
        if not req:
            return {"ok": False, "error": "request_not_found"}

        vendor = self._vendors.get(req.vendor_id)
        if not vendor or not vendor.active:
            req.status = PurchaseStatus.DENIED
            reasons = ["inactive_or_missing_vendor"]
            return {"ok": True, "status": req.status.value, "reasons": reasons}

        # Evaluate SE41 numeric merit
        eval_out = self._validator.evaluate(req, vendor, self._budget)
        if not eval_out.get("valid"):
            req.status = PurchaseStatus.ON_HOLD
            return {"ok": True, "status": req.status.value, "reasons": ["se41_invalid"]}

        req.se41_numeric_score = float(eval_out["score"])
        # ethos decision (uses Four Pillars; we pass minimal signals context)
        ethos = ethos_decision(eval_out["signals"])
        req.ethos_gate = ethos["decision"]
        req.ethos_reasons = ethos.get("reasons", [])
        req.se41 = None  # (optional) keep light; heavy packet would be SE41Signals

        # Budget pressure guardrail: preserve safety buffer.
        projected_commit = self._budget.committed + req.cost
        projected_avail = self._budget.spend_limit - projected_commit
        buffer_floor = self._budget.spend_limit * self._budget.safety_buffer
        budget_ok = projected_avail >= buffer_floor

        status = PurchaseStatus.UNDER_REVIEW
        reasons: List[str] = []
        if req.ethos_gate == "deny":
            status = PurchaseStatus.DENIED
            reasons += ["ethos_deny"]
        elif not budget_ok:
            status = PurchaseStatus.ON_HOLD
            reasons += ["budget_safety_buffer_breach"]
        elif req.se41_numeric_score < 0.55:
            status = PurchaseStatus.ON_HOLD
            reasons += ["low_symbolic_merit"]

        req.status = status
        return {
            "ok": True,
            "request_id": request_id,
            "status": status.value,
            "se41_merit": round(req.se41_numeric_score, 4),
            "ethos": req.ethos_gate,
            "reasons": reasons or req.ethos_reasons,
        }

    def approve_request(
        self, request_id: str, approver: str = "system"
    ) -> PurchaseDecision:
        req = self._requests.get(request_id)
        if not req:
            raise ValueError("request_not_found")

        if req.status in (PurchaseStatus.DENIED, PurchaseStatus.CANCELLED):
            raise ValueError(f"cannot_approve_status_{req.status.value}")

        # Final budget check
        projected = self._budget.committed + req.cost
        if projected > self._budget.spend_limit:
            req.status = PurchaseStatus.ON_HOLD
            dec = PurchaseDecision(
                decision_id=f"dec_{uuid.uuid4().hex[:10]}",
                request_id=request_id,
                status=req.status,
                approver=approver,
                reasons=["exceeds_fiscal_limit"],
                budget_snapshot=self._budget,
            )
            self._decisions[dec.decision_id] = dec
            return dec

        # Approve
        req.status = PurchaseStatus.APPROVED
        self._budget.committed = projected
        self._budget.available = self._budget.spend_limit - self._budget.committed

        # Create PO
        po = PurchaseOrder(
            po_id=f"po_{uuid.uuid4().hex[:10]}",
            request_id=request_id,
            vendor_id=req.vendor_id,
            cost=req.cost,
            invoice_due_at=(
                datetime.now() + timedelta(days=30) if not req.is_recurring else None
            ),
            terms={"term_months": req.term_months, "recurring": req.is_recurring},
            notes=f"{req.title} | {req.description[:120]}...",
        )
        self._pos[po.po_id] = po

        dec = PurchaseDecision(
            decision_id=f"dec_{uuid.uuid4().hex[:10]}",
            request_id=request_id,
            status=PurchaseStatus.APPROVED,
            approver=approver,
            reasons=["se41_ok", f"ethos_{req.ethos_gate}"],
            se41_snapshot={"score": req.se41_numeric_score, "ethos": req.ethos_gate},
            budget_snapshot=self._budget,
        )
        self._decisions[dec.decision_id] = dec
        self.logger.info(
            f"[Approve] {request_id} -> {po.po_id}  committed=${self._budget.committed:,.2f}"
        )
        return dec

    def fulfill_request(
        self, request_id: str, notes: str = ""
    ) -> Optional[PurchaseOrder]:
        # Mark PO fulfilled / activated
        for po in self._pos.values():
            if po.request_id == request_id and po.status == PurchaseStatus.APPROVED:
                po.status = PurchaseStatus.FULFILLED
                po.activated_at = datetime.now()
                if notes:
                    po.notes = f"{po.notes}\n{notes}"
                self.logger.info(f"[Fulfill] {po.po_id} -> activated")
                return po
        return None

    def cancel_request(
        self, request_id: str, reason: str = "requester_cancelled"
    ) -> bool:
        req = self._requests.get(request_id)
        if not req:
            return False
        # If already approved, roll back committed budget
        if req.status == PurchaseStatus.APPROVED:
            # Find the PO to reverse
            for po in self._pos.values():
                if po.request_id == request_id and po.status == PurchaseStatus.APPROVED:
                    self._budget.committed -= po.cost
                    self._budget.available = (
                        self._budget.spend_limit - self._budget.committed
                    )
                    po.status = PurchaseStatus.CANCELLED
                    po.notes = f"{po.notes}\nCANCELLED: {reason}"
                    break
        req.status = PurchaseStatus.CANCELLED
        self.logger.info(f"[Cancel] {request_id} ({reason})")
        return True

    # ---------------- reporting ------------------

    def budget_status(self) -> Dict[str, Any]:
        return {
            "as_of": self._budget.as_of.isoformat(),
            "fiscal_year": self._budget.fiscal_year,
            "spend_limit": self._budget.spend_limit,
            "committed": self._budget.committed,
            "available": self._budget.available,
            "safety_buffer": self._budget.safety_buffer,
        }

    def list_requests(
        self, status: Optional[PurchaseStatus] = None
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for r in self._requests.values():
            if status and r.status != status:
                continue
            out.append(
                {
                    "id": r.request_id,
                    "title": r.title,
                    "vendor": r.vendor_id,
                    "type": r.purchase_type.value,
                    "priority": r.priority.name,
                    "cost": r.cost,
                    "status": r.status.value,
                    "merit": round(r.se41_numeric_score, 4),
                    "ethos": r.ethos_gate,
                }
            )
        return out

    def list_pos(self, status: Optional[PurchaseStatus] = None) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for po in self._pos.values():
            if status and po.status != status:
                continue
            out.append(
                {
                    "po_id": po.po_id,
                    "request_id": po.request_id,
                    "vendor": po.vendor_id,
                    "cost": po.cost,
                    "status": po.status.value,
                    "due": po.invoice_due_at.isoformat() if po.invoice_due_at else None,
                }
            )
        return out


# ----------------- convenience factory & smoke -------------------------------


def create_purchase_manager(**kwargs) -> PurchaseManager:
    return PurchaseManager(**kwargs)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    pm = create_purchase_manager(spend_limit=100_000.0, safety_buffer=0.15)
    v = pm.register_vendor(
        "Mercury DataCloud",
        PurchaseType.CLOUD_INFRA,
        reliability=0.92,
        integrity=0.9,
        enrichment=0.88,
    )

    req = pm.submit_request(
        title="Realtime L2 Feed + 90-day history",
        description="Consolidated equities L2 with burst credits for earnings season.",
        vendor_id=v.vendor_id,
        ptype=PurchaseType.DATA_FEED,
        priority=PurchasePriority.HIGH,
        cost=18_000.0,
        term_months=12,
        is_recurring=True,
        business_value=0.85,
        operational_need=0.75,
        risk_mitigation=0.35,
        alignment_note="Supports HFT and OMS slippage control.",
    )

    print("Review:", pm.review_request(req.request_id))
    dec = pm.approve_request(req.request_id, approver="CFO")
    print("Approved:", dec.status.value, pm.budget_status())
    po = pm.fulfill_request(
        req.request_id, notes="Activated in prod. SLA monitor linked."
    )
    print("PO:", po.status.value if po else None)
